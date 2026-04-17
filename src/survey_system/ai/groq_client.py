"""HTTP client for Groq OpenAI-compatible chat completions."""

from __future__ import annotations

import json
from typing import Any

import httpx

from survey_system.exceptions import LLMError


def _client_kwargs(timeout: float, proxy: str | None) -> dict[str, Any]:
    """Build kwargs for ``httpx.Client`` (proxy + env proxy support)."""
    kwargs: dict[str, Any] = {
        "timeout": timeout,
        "trust_env": True,
    }
    if proxy:
        kwargs["proxy"] = proxy
    return kwargs


class GroqClient:
    """Minimal Groq chat client (sync)."""

    _CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
        http_client: httpx.Client | None = None,
        proxy: str | None = None,
    ) -> None:
        """Create a client.

        Args:
            api_key: Groq API key.
            model: Model id (e.g. ``llama-3.3-70b-versatile``).
            timeout_seconds: HTTP timeout when using the default client.
            http_client: Optional injected client (used by tests).
            proxy: Optional explicit proxy URL for HTTPS (overrides env when set).

        Note:
            With no ``proxy`` and ``http_client``, ``trust_env=True`` applies so
            ``HTTPS_PROXY`` / ``HTTP_PROXY`` from the environment still work.
        """
        if not api_key:
            raise LLMError("Groq API key is empty", details={})
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._http_client = http_client
        self._proxy = proxy.strip() if proxy else None

    def chat_completion_json(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Request a JSON object response from the chat model.

        Args:
            system: System prompt.
            user: User prompt.
            temperature: Sampling temperature.

        Returns:
            Parsed JSON object from the assistant message.

        Raises:
            LLMError: On HTTP/network/parse failures.
        """
        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self._http_client is not None:
                response = self._http_client.post(self._CHAT_URL, headers=headers, json=payload)
            else:
                kw = _client_kwargs(self._timeout, self._proxy)
                with httpx.Client(**kw) as client:
                    response = client.post(self._CHAT_URL, headers=headers, json=payload)
        except httpx.ConnectError as exc:
            raise LLMError(
                "Groq tak network se jude nahi (DNS / internet). "
                "Internet aur DNS check karein; VPN/firewall kabhi api.groq.com block karte hain. "
                "Office network ho to `.env` mein HTTPS_PROXY set karein.",
                details={
                    "stage": "connect",
                    "host": "api.groq.com",
                    "error": repr(exc),
                },
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMError(
                "Groq API ne time limit ke andar jawab nahi diya (timeout). Dobara try karein.",
                details={"stage": "timeout", "error": repr(exc)},
            ) from exc
        except httpx.RequestError as exc:
            raise LLMError(
                "Groq HTTP request fail (network). Connection / proxy check karein.",
                details={"stage": "http", "error": repr(exc)},
            ) from exc
        except Exception as exc:
            raise LLMError(
                "Groq HTTP request failed",
                details={"stage": "http", "original_type": type(exc).__name__},
            ) from exc

        if response.status_code >= 400:
            raise LLMError(
                "Groq API returned an error",
                details={
                    "status_code": response.status_code,
                    "body": response.text[:2000],
                },
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("unexpected message content type")
            return json.loads(content)
        except Exception as exc:
            raise LLMError(
                "failed to parse Groq JSON response",
                details={"error": type(exc).__name__},
            ) from exc
