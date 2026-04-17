"""Tests for Groq client (HTTP mocked)."""

from __future__ import annotations

import httpx

from survey_system.ai.groq_client import GroqClient


def test_chat_completion_json_parses_payload() -> None:
    """Successful Groq response is parsed into a JSON dict."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"value": 1, "confidence": 0.9}',
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    groq = GroqClient(api_key="test", model="m", http_client=client)
    data = groq.chat_completion_json(system="s", user="u")
    assert data["value"] == 1


def test_http_error_raises() -> None:
    """Non-2xx responses raise ``LLMError``."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    groq = GroqClient(api_key="test", model="m", http_client=client)

    from survey_system.exceptions import LLMError

    try:
        groq.chat_completion_json(system="s", user="u")
    except LLMError as exc:
        assert exc.details is not None
        assert exc.details.get("status_code") == 500
    else:
        raise AssertionError("expected LLMError")
