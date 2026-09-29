import re
from dataclasses import dataclass

from django.conf import settings

# Deliberately conservative: a detected credential prevents the whole file from
# reaching the vector database. False positives are safer than indexing secrets.
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", re.I),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"),
]

CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

@dataclass(frozen=True)
class ContentSecurityResult:
    safe: bool
    reason: str
    text: str


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def redact_local_pii(text: str) -> str:
    text = CPF.sub("[CPF-MASCARADO]", text)
    return EMAIL.sub("[EMAIL-MASCARADO]", text)


async def redact_pii(text: str) -> str:
    """Mask PII before embedding. Presidio is additive to local deterministic rules."""
    redacted = redact_local_pii(text)
    if not settings.PRESIDIO_ENABLED or not redacted.strip():
        return redacted

    import httpx

    payload = {
        "text": redacted,
        "language": settings.PRESIDIO_LANGUAGE,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.PRESIDIO_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.PRESIDIO_ANALYZER_URL.rstrip("/") + "/analyze", json=payload)
            response.raise_for_status()
            findings = response.json()
    except Exception:
        if settings.PRESIDIO_FAIL_CLOSED:
            raise
        return redacted

    # Replace from the end so offsets returned by Presidio remain valid.
    for item in sorted(findings, key=lambda x: int(x.get("start", 0)), reverse=True):
        start, end = int(item.get("start", 0)), int(item.get("end", 0))
        if 0 <= start < end <= len(redacted):
            entity = str(item.get("entity_type", "PII"))
            redacted = redacted[:start] + f"[{entity}-MASCARADO]" + redacted[end:]
    return redacted


async def inspect_repository_content(text: str) -> ContentSecurityResult:
    if contains_secret(text):
        return ContentSecurityResult(False, "secret_detected", "")
    return ContentSecurityResult(True, "sanitized", await redact_pii(text))
