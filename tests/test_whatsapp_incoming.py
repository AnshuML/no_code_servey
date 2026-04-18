"""Tests for Meta WhatsApp webhook JSON parsing."""

from __future__ import annotations

from survey_system.whatsapp.incoming import parse_incoming_text_messages


def test_parse_sample_cloud_api_payload() -> None:
    """Extract one text message from a typical Cloud API body."""
    body = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": "123",
                            },
                            "contacts": [{"profile": {"name": "User"}, "wa_id": "919811111111"}],
                            "messages": [
                                {
                                    "from": "919811111111",
                                    "id": "wamid.x",
                                    "timestamp": "1",
                                    "type": "text",
                                    "text": {"body": "hello"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    msgs = parse_incoming_text_messages(body)
    assert len(msgs) == 1
    assert msgs[0].wa_from_id == "919811111111"
    assert msgs[0].body == "hello"


def test_parse_ignores_non_text() -> None:
    """Non-text messages are skipped."""
    body = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messages": [{"from": "1", "type": "image"}]}}]}],
    }
    assert parse_incoming_text_messages(body) == []
