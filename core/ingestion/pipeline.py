import hashlib
import logging
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import quote

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.ingestion.security import inspect_repository_content
from core.llm.ollama import embed
from knowledge.models import KnowledgeChunk, Project

logger = logging.getLogger(__name__)

BLOCKED_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", ".npmrc", ".pypirc",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
}
BLOCKED_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".sqlite", ".sqlite3",
    ".db", ".dump", ".bak", ".backup", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".pdf", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pptx", ".jar", ".war", ".class", ".exe", ".dll",
    ".so", ".dylib", ".bin", ".woff", ".woff2", ".ttf", ".eot",
}
ALLOWED_EXTENSIONLESS_NAMES = {"dockerfile", "makefile", "jenkinsfile"}
BLOCKED_PARTS = {
    ".git", "node_modules", "vendor", "dist", "build", "coverage", ".venv", "venv",
    "__pycache__", "uploads", "media", "backups", "backup", "dumps", "dump",
}

@dataclass(frozen=True)
class IngestionStats:
    project_id: int
    repository: str
    sha: str
    files_seen: int = 0
    files_indexed: int = 0
    files_skipped: int = 0
    files_secret_blocked: int = 0
    chunks_written: int = 0
    unchanged: bool = False

    def as_dict(self):
        return self.__dict__.copy()


def is_allowed_path(path: str, size: int | None = None) -> bool:
    p = PurePosixPath(path)
    lower_parts = {part.lower() for part in p.parts}
    name = p.name.lower()
    if not path or name in BLOCKED_NAMES or lower_parts.intersection(BLOCKED_PARTS):
        return False
    if name.startswith(".env."):
        return False
    if p.suffix.lower() in BLOCKED_SUFFIXES:
        return False
    if size is not None and size > settings.INGEST_MAX_FILE_BYTES:
        return False
    if settings.INGEST_ALLOWED_EXTENSIONS and p.suffix.lower() not in settings.INGEST_ALLOWED_EXTENSIONS and name not in ALLOWED_EXTENSIONLESS_NAMES:
        return False
    return True


def chunk_text(text: str) -> list[str]:
    text = text.replace("\x00", "").strip()
    if not text:
        return []
    size = settings.INGEST_CHUNK_CHARS
    overlap = min(settings.INGEST_CHUNK_OVERLAP, max(0, size - 1))
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        piece = text[start:end]
        if end < len(text):
            # Prefer a line boundary without making chunks arbitrarily small.
            cut = piece.rfind("\n", max(1, size // 2))
            if cut > 0:
                end = start + cut + 1
                piece = text[start:end]
        piece = piece.strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def _source_url(project: Project, path: str, ref: str) -> str:
    if project.provider == Project.Provider.GITHUB:
        return f"{project.web_url.rstrip('/')}/blob/{quote(ref, safe='')}/{quote(path, safe='/')}"
    return project.web_url


def _replace_chunks(project_id: int, rows: list[dict], repository_sha: str) -> int:
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        KnowledgeChunk.objects.filter(project=project, source_type="repository_file").delete()
        KnowledgeChunk.objects.bulk_create([
            KnowledgeChunk(project=project, **row) for row in rows
        ], batch_size=250)
        project.last_repository_sha = repository_sha
        project.indexed_at = timezone.now()
        project.save(update_fields=["last_repository_sha", "indexed_at"])
    return len(rows)


async def ingest_project(provider, project: Project, force: bool = False) -> IngestionStats:
    if not project.enabled:
        raise ValueError("Projeto desabilitado não pode ser indexado.")
    branch_name = project.default_branch or "main"
    branch = await provider.branch(project.path_with_namespace, branch_name)
    commit = branch.get("commit") or {}
    commit_sha = str(commit.get("sha") or "")
    tree_sha = str(((commit.get("commit") or {}).get("tree") or {}).get("sha") or commit_sha)
    if not commit_sha:
        raise ValueError(f"Não foi possível determinar o SHA de {project.path_with_namespace}.")

    if not force and project.last_repository_sha == commit_sha:
        return IngestionStats(project.id, project.path_with_namespace, commit_sha, unchanged=True)

    tree = await provider.repository_tree(project.path_with_namespace, tree_sha)
    rows: list[dict] = []
    files_seen = files_indexed = files_skipped = files_secret_blocked = 0

    for item in tree:
        if item.get("type") != "blob":
            continue
        files_seen += 1
        path = str(item.get("path") or "")
        if not is_allowed_path(path, item.get("size")):
            files_skipped += 1
            continue
        raw = await provider.raw_file(project.path_with_namespace, path, commit_sha)
        if len(raw.encode("utf-8", errors="ignore")) > settings.INGEST_MAX_FILE_BYTES:
            files_skipped += 1
            continue
        security = await inspect_repository_content(raw)
        if not security.safe:
            files_secret_blocked += 1
            logger.warning("ingestion_file_blocked project=%s path=%s reason=%s", project.path_with_namespace, path, security.reason)
            continue
        chunks = chunk_text(security.text)
        if not chunks:
            files_skipped += 1
            continue
        vectors = []
        for offset in range(0, len(chunks), settings.INGEST_EMBED_BATCH_SIZE):
            vectors.extend(await embed(chunks[offset:offset + settings.INGEST_EMBED_BATCH_SIZE]))
        if len(vectors) != len(chunks):
            raise RuntimeError("O provedor de embeddings retornou quantidade inesperada de vetores.")
        for index, (content, vector) in enumerate(zip(chunks, vectors)):
            if len(vector) != settings.INGEST_EMBED_DIMENSIONS:
                raise RuntimeError(f"Embedding com dimensão {len(vector)}; esperado {settings.INGEST_EMBED_DIMENSIONS}.")
            rows.append({
                "source_type": "repository_file",
                "source_key": path,
                "chunk_index": index,
                "title": path,
                "source_url": _source_url(project, path, commit_sha),
                "ref": commit_sha,
                "content": content,
                "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "metadata_json": {"path": path, "branch": branch_name, "commit_sha": commit_sha},
                "embedding": vector,
            })
        files_indexed += 1

    written = await sync_to_async(_replace_chunks)(project.id, rows, commit_sha)
    return IngestionStats(
        project.id, project.path_with_namespace, commit_sha,
        files_seen, files_indexed, files_skipped, files_secret_blocked, written, False,
    )
