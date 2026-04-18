"""Parse Meta WhatsApp Business ``messages`` webhook payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IncomingText:
    """One inbound user text message."""

    wa_from_id: str
    body: str


def parse_incoming_text_messages(payload: dict[str, Any]) -> list[IncomingText]:
    """Extract user text messages from a Cloud API webhook JSON body.

    Ignores status updates, non-text types, and malformed entries.
    """
    out: list[IncomingText] = []
    if payload.get("object") != "whatsapp_business_account":
        return out
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            for msg in value.get("messages") or []:
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") != "text":
                    continue
                from_id = msg.get("from")
                if not isinstance(from_id, str) or not from_id.strip():
                    continue
                text_obj = msg.get("text")
                if not isinstance(text_obj, dict):
                    continue
                body = text_obj.get("body")
                if not isinstance(body, str):
                    continue
                out.append(IncomingText(wa_from_id=from_id.strip(), body=body))
    return out
