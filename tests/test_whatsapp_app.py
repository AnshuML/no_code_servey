"""FastAPI WhatsApp webhook (verify handshake)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from survey_system.config import Environment, Settings
from survey_system.whatsapp.app import create_whatsapp_app


def test_get_webhook_returns_challenge_when_token_matches() -> None:
    s = Settings(
        _env_file=None,
        environment=Environment.DEV,
        groq_api_key="dummy",
        whatsapp_verify_token="mytoken",
    )
    app = create_whatsapp_app(s)
    client = TestClient(app)
    r = client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "mytoken",
            "hub.challenge": "CHALLENGE_OK",
        },
    )
    assert r.status_code == 200
    assert r.text == "CHALLENGE_OK"


def test_get_webhook_help_page_without_meta_params() -> None:
    """Opening webhook in a browser (no query) returns HTML help, not DNS client error."""
    s = Settings(
        _env_file=None,
        environment=Environment.DEV,
        groq_api_key="dummy",
        whatsapp_verify_token="mytoken",
    )
    app = create_whatsapp_app(s)
    client = TestClient(app)
    r = client.get("/webhook/whatsapp")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "NXDOMAIN" in r.text or "ngrok" in r.text.lower()


def test_get_webhook_403_on_bad_token() -> None:
    s = Settings(
        _env_file=None,
        environment=Environment.DEV,
        groq_api_key="dummy",
        whatsapp_verify_token="mytoken",
    )
    app = create_whatsapp_app(s)
    client = TestClient(app)
    r = client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "x",
        },
    )
    assert r.status_code == 403
