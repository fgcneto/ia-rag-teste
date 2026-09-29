import asyncio

import httpx
import pytest

from core.ingestion.pipeline import chunk_text, is_allowed_path
from core.ingestion.security import (
    contains_secret,
    inspect_repository_content,
    redact_local_pii,
    redact_pii,
)


def test_sensitive_paths_are_never_ingested(settings):
    settings.INGEST_ALLOWED_EXTENSIONS = {".py", ".md", ".txt"}
    settings.INGEST_MAX_FILE_BYTES = 1024

    blocked = [
        ".env",
        ".env.production",
        "config/.env.production",
        "certs/server.pem",
        "certs/server.key",
        "certs/server.p12",
        "backup/database.dump",
        "backups/database.txt",
        "node_modules/pkg/index.js",
        ".git/config",
        "uploads/patient.txt",
        "media/export.txt",
    ]

    for path in blocked:
        assert not is_allowed_path(path), path

    assert is_allowed_path("src/service.py", 100)


def test_file_size_limit_is_enforced(settings):
    settings.INGEST_ALLOWED_EXTENSIONS = {".py"}
    settings.INGEST_MAX_FILE_BYTES = 100

    assert is_allowed_path("src/allowed.py", 100)
    assert not is_allowed_path("src/huge.py", 101)


@pytest.mark.parametrize(
    "content",
    [
        "-----BEGIN PRIVATE KEY-----\nfake-test-material",
        "-----BEGIN RSA PRIVATE KEY-----\nfake-test-material",
        'api_key = "synthetic-secret-value-123"',
        'password = "synthetic-password-123"',
        "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "github_pat_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "AKIA" + "ABCDEFGHIJKLMNOP",
    ],
)
def test_secret_detection_blocks_synthetic_credentials(content):
    assert contains_secret(content)


def test_environment_variable_reference_is_not_treated_as_secret():
    assert not contains_secret('api_key = os.getenv("API_KEY")')
    assert not contains_secret('token = os.environ["SERVICE_TOKEN"]')


def test_local_pii_is_masked_before_embedding():
    text = "Contato: dev@example.org CPF 123.456.789-00"

    masked = redact_local_pii(text)

    assert "dev@example.org" not in masked
    assert "123.456.789-00" not in masked
    assert "[EMAIL-MASCARADO]" in masked
    assert "[CPF-MASCARADO]" in masked


def test_repository_content_with_secret_is_rejected_before_pii():
    content = 'api_key = "synthetic-secret-value-123"'

    result = asyncio.run(
        inspect_repository_content(content)
    )

    assert result.safe is False
    assert result.reason == "secret_detected"
    assert result.text == ""


def test_repository_content_masks_local_pii_when_presidio_disabled(
    settings,
):
    settings.PRESIDIO_ENABLED = False

    content = (
        "Contato dev@example.org "
        "CPF 123.456.789-00"
    )

    result = asyncio.run(
        inspect_repository_content(content)
    )

    assert result.safe is True
    assert result.reason == "sanitized"
    assert "dev@example.org" not in result.text
    assert "123.456.789-00" not in result.text
    assert "[EMAIL-MASCARADO]" in result.text
    assert "[CPF-MASCARADO]" in result.text


def test_presidio_failure_is_fail_closed(
    settings,
    monkeypatch,
):
    settings.PRESIDIO_ENABLED = True
    settings.PRESIDIO_FAIL_CLOSED = True
    settings.PRESIDIO_ANALYZER_URL = "http://presidio.invalid"
    settings.PRESIDIO_LANGUAGE = "en"
    settings.PRESIDIO_TIMEOUT_SECONDS = 1

    async def fail_post(self, *args, **kwargs):
        raise httpx.ConnectError("synthetic presidio outage")

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        fail_post,
    )

    with pytest.raises(httpx.ConnectError):
        asyncio.run(
            redact_pii("Texto técnico sem PII local.")
        )


def test_presidio_failure_can_use_local_redaction_when_fail_open(
    settings,
    monkeypatch,
):
    settings.PRESIDIO_ENABLED = True
    settings.PRESIDIO_FAIL_CLOSED = False
    settings.PRESIDIO_ANALYZER_URL = "http://presidio.invalid"
    settings.PRESIDIO_LANGUAGE = "en"
    settings.PRESIDIO_TIMEOUT_SECONDS = 1

    async def fail_post(self, *args, **kwargs):
        raise httpx.ConnectError("synthetic presidio outage")

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        fail_post,
    )

    result = asyncio.run(
        redact_pii(
            "Contato dev@example.org CPF 123.456.789-00"
        )
    )

    assert "dev@example.org" not in result
    assert "123.456.789-00" not in result
    assert "[EMAIL-MASCARADO]" in result
    assert "[CPF-MASCARADO]" in result


def test_chunking_has_overlap_and_no_empty_chunks(settings):
    settings.INGEST_CHUNK_CHARS = 40
    settings.INGEST_CHUNK_OVERLAP = 8

    text = (
        "linha um com texto\n"
        "linha dois com texto\n"
        "linha tres com texto\n"
    )

    chunks = chunk_text(text)

    assert len(chunks) >= 2
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 40 for chunk in chunks)
