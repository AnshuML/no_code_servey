"""Outbound channel port (future: Telegram, Matrix, WhatsApp webhooks — OSS bots)."""

from __future__ import annotations

from typing import Protocol


class OutboundChannel(Protocol):
    """Send a text turn to a respondent; implementation chooses transport."""

    def send_text(self, *, to_address: str, text: str) -> None:
        """Deliver one message chunk (idempotent if your backend requires it)."""
        ...
