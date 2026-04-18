"""Meta webhook signature verification."""

from __future__ import annotations

import hashlib
import hmac

from survey_system.whatsapp.security import verify_meta_webhook_signature


def test_skips_verify_when_no_secret() -> None:
    assert verify_meta_webhook_signature("", None, b"{}") is True


def test_rejects_bad_signature() -> None:
    secret = "mysecret"
    body = b'{"x":1}'
    bad = "sha256=deadbeef"
    assert verify_meta_webhook_signature(secret, bad, body) is False


def test_accepts_valid_signature() -> None:
    secret = "mysecret"
    body = b'{"x":1}'
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    good = f"sha256={expected}"
    assert verify_meta_webhook_signature(secret, good, body) is True
