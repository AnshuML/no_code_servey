"""Send WhatsApp Cloud API messages (any user's ``wa_id``)."""

from __future__ import annotations

from typing import Any

import httpx

from survey_system.config import Settings
from survey_system.exceptions import SurveySystemError


def _client_kwargs(timeout: float, proxy: str | None) -> dict[str, Any]:
    kw: dict[str, Any] = {"timeout": timeout, "trust_env": True}
    if proxy:
        kw["proxy"] = proxy
    return kw


class MetaWhatsAppSender:
    """POST ``/messages`` to Graph API — works for every respondent number Meta sends as ``from``."""

    def __init__(
        self,
        settings: Settings,
        *,
        timeout_seconds: float = 60.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._token = settings.whatsapp_access_token.strip()
        self._phone_number_id = settings.whatsapp_phone_number_id.strip()
        self._version = settings.whatsapp_graph_api_version.strip().lstrip("/")
        self._proxy = settings.https_proxy.strip() or None
        self._timeout = timeout_seconds
        self._http = http_client

    @property
    def is_configured(self) -> bool:
        return bool(self._token and self._phone_number_id)

    def send_text(self, to_wa_id: str, body: str) -> None:
        """Send one text bubble to ``to_wa_id`` (digits, country code, no ``+``)."""
        if not self.is_configured:
            raise SurveySystemError(
                "WhatsApp send is not configured (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID).",
                details={},
            )
        url = (
            f"https://graph.facebook.com/{self._version}/"
            f"{self._phone_number_id}/messages"
        )
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to_wa_id,
            "type": "text",
            "text": {"preview_url": False, "body": body[:4096]},
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        try:
            if self._http is not None:
                resp = self._http.post(url, headers=headers, json=payload)
            else:
                with httpx.Client(**_client_kwargs(self._timeout, self._proxy)) as client:
                    resp = client.post(url, headers=headers, json=payload)
        except httpx.RequestError as exc:
            raise SurveySystemError(
                "WhatsApp Graph API request failed",
                details={"error": repr(exc)},
            ) from exc

        if resp.status_code >= 400:
            raise SurveySystemError(
                "WhatsApp Graph API returned an error",
                details={"status_code": resp.status_code, "body": resp.text[:2000]},
            )
