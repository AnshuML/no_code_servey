"""Optional Meta ``X-Hub-Signature-256`` verification."""

from __future__ import annotations

import hashlib
import hmac


def verify_meta_webhook_signature(
    app_secret: str,
    signature_header: str | None,
    raw_body: bytes,
) -> bool:
    """Return True if signature matches or ``app_secret`` is empty (skip verify)."""
    if not app_secret.strip():
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature_header[7:], expected)
