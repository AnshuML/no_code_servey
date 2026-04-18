"""Multi-user WhatsApp orchestrator (in-memory sessions)."""

from __future__ import annotations

from unittest.mock import MagicMock

from survey_system.whatsapp.orchestrator import WhatsAppSurveyOrchestrator


def test_two_users_each_complete_one_question() -> None:
    """Different ``wa_id`` each finish a one-question survey independently."""
    engine = MagicMock()
    engine.parse_answer.return_value = {"value": "ok", "confidence": 1.0}
    engine.validate_answer.return_value = {"valid": True, "issues": []}
    one_q = {
        "id": "s",
        "title": "t",
        "questions": [{"id": "q1", "text": "Naam?", "type": "free_text"}],
    }
    orch = WhatsAppSurveyOrchestrator(one_q, engine, persistence=None)
    r_a = orch.handle_message("91AAA", "Ravi")
    r_b = orch.handle_message("91BBB", "Sita")
    assert any("complete" in part.lower() for part in r_a)
    assert any("complete" in part.lower() for part in r_b)


def test_reset_starts_fresh() -> None:
    """RESET clears and re-opens survey."""
    engine = MagicMock()
    engine.parse_answer.return_value = {"value": "x", "confidence": 1.0}
    engine.validate_answer.return_value = {"valid": True, "issues": []}

    tiny = {
        "id": "t",
        "title": "T",
        "questions": [{"id": "q1", "text": "Name?", "type": "free_text"}],
    }
    orch = WhatsAppSurveyOrchestrator(tiny, engine, persistence=None)
    r = orch.handle_message("999", "reset")
    assert any("Survey shuru" in part for part in r)
