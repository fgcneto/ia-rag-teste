import asyncio

import pytest

from core.ingestion import pipeline
from knowledge.models import KnowledgeChunk, Project


class FakeProvider:
    def __init__(self, raw_content, sha="new-test-sha"):
        self.raw_content = raw_content
        self.sha = sha

    async def branch(self, repository, branch_name):
        return {
            "commit": {
                "sha": self.sha,
                "commit": {
                    "tree": {
                        "sha": "synthetic-tree-sha",
                    }
                },
            }
        }

    async def repository_tree(self, repository, tree_sha):
        return [
            {
                "type": "blob",
                "path": "src/example.py",
                "size": len(self.raw_content.encode("utf-8")),
            }
        ]

    async def raw_file(self, repository, path, ref):
        return self.raw_content


@pytest.mark.django_db(transaction=True)
def test_only_sanitized_content_reaches_embedding(
    settings,
    monkeypatch,
):
    settings.PRESIDIO_ENABLED = False
    settings.INGEST_ALLOWED_EXTENSIONS = {".py"}
    settings.INGEST_MAX_FILE_BYTES = 10000
    settings.INGEST_CHUNK_CHARS = 1600
    settings.INGEST_CHUNK_OVERLAP = 200
    settings.INGEST_EMBED_BATCH_SIZE = 16
    settings.INGEST_EMBED_DIMENSIONS = 768

    project = Project.objects.create(
        provider=Project.Provider.GITHUB,
        external_id="security-test-sanitized",
        path_with_namespace="synthetic/security-test",
        name="security-test",
        web_url="https://example.invalid/synthetic/security-test",
        default_branch="main",
        enabled=True,
    )

    raw_email = "developer@example.org"
    raw_cpf = "123.456.789-00"

    provider = FakeProvider(
        (
            "# synthetic repository content\n"
            f'CONTACT = "{raw_email}"\n'
            f'CPF = "{raw_cpf}"\n'
        )
    )

    received_by_embedding = []

    async def fake_embed(texts):
        received_by_embedding.extend(texts)
        return [
            [0.0] * settings.INGEST_EMBED_DIMENSIONS
            for _ in texts
        ]

    monkeypatch.setattr(
        pipeline,
        "embed",
        fake_embed,
    )

    result = asyncio.run(
        pipeline.ingest_project(
            provider,
            project,
            force=True,
        )
    )

    assert result.files_indexed == 1
    assert result.chunks_written >= 1
    assert received_by_embedding

    embedded_text = "\n".join(received_by_embedding)

    assert raw_email not in embedded_text
    assert raw_cpf not in embedded_text
    assert "[EMAIL-MASCARADO]" in embedded_text
    assert "[CPF-MASCARADO]" in embedded_text

    stored_text = "\n".join(
        KnowledgeChunk.objects
        .filter(project=project)
        .values_list("content", flat=True)
    )

    assert raw_email not in stored_text
    assert raw_cpf not in stored_text
    assert "[EMAIL-MASCARADO]" in stored_text
    assert "[CPF-MASCARADO]" in stored_text


@pytest.mark.django_db(transaction=True)
def test_invalid_embedding_dimension_preserves_existing_chunks(
    settings,
    monkeypatch,
):
    settings.PRESIDIO_ENABLED = False
    settings.INGEST_ALLOWED_EXTENSIONS = {".py"}
    settings.INGEST_MAX_FILE_BYTES = 10000
    settings.INGEST_CHUNK_CHARS = 1600
    settings.INGEST_CHUNK_OVERLAP = 200
    settings.INGEST_EMBED_BATCH_SIZE = 16
    settings.INGEST_EMBED_DIMENSIONS = 768

    project = Project.objects.create(
        provider=Project.Provider.GITHUB,
        external_id="security-test-dimension",
        path_with_namespace="synthetic/dimension-test",
        name="dimension-test",
        web_url="https://example.invalid/synthetic/dimension-test",
        default_branch="main",
        last_repository_sha="previous-safe-sha",
        enabled=True,
    )

    original = KnowledgeChunk.objects.create(
        project=project,
        source_type="repository_file",
        source_key="src/original.py",
        chunk_index=0,
        title="src/original.py",
        source_url=(
            "https://example.invalid/"
            "synthetic/dimension-test/blob/"
            "previous-safe-sha/src/original.py"
        ),
        ref="previous-safe-sha",
        content="ORIGINAL_SAFE_CONTENT",
        content_hash="synthetic-original-hash",
        metadata_json={
            "path": "src/original.py",
            "branch": "main",
            "commit_sha": "previous-safe-sha",
        },
        embedding=[0.0] * 768,
    )

    original_id = original.id

    provider = FakeProvider(
        'VALUE = "new synthetic content"\n',
        sha="new-invalid-sha",
    )

    async def invalid_embed(texts):
        return [
            [0.0] * 767
            for _ in texts
        ]

    monkeypatch.setattr(
        pipeline,
        "embed",
        invalid_embed,
    )

    with pytest.raises(
        RuntimeError,
        match="Embedding com dimensão 767",
    ):
        asyncio.run(
            pipeline.ingest_project(
                provider,
                project,
                force=True,
            )
        )

    project.refresh_from_db()

    chunks = list(
        KnowledgeChunk.objects
        .filter(project=project)
        .values(
            "id",
            "content",
            "ref",
            "source_key",
        )
    )

    assert project.last_repository_sha == "previous-safe-sha"
    assert len(chunks) == 1
    assert chunks[0]["id"] == original_id
    assert chunks[0]["content"] == "ORIGINAL_SAFE_CONTENT"
    assert chunks[0]["ref"] == "previous-safe-sha"
    assert chunks[0]["source_key"] == "src/original.py"
