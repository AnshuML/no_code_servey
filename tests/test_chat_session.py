"""Tests for chat session orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock

from survey_system.chat.session import SurveyChatSession
from survey_system.schema.survey import END_SURVEY_NAV, survey_from_dict


def test_completes_single_question_survey() -> None:
    """A valid answer completes a one-question survey."""
    survey = survey_from_dict(
        {
            "id": "s1",
            "title": "t",
            "questions": [{"id": "q1", "text": "Your name?", "type": "free_text"}],
        }
    )
    engine = MagicMock()
    engine.parse_answer.return_value = {"value": "Ada", "confidence": 1.0}
    engine.validate_answer.return_value = {"valid": True, "issues": []}

    sess = SurveyChatSession(survey=survey, engine=engine)
    r = sess.submit_user_text("Ada")
    assert r["status"] == "complete"
    assert sess.answers["q1"] == "Ada"


def test_needs_clarification_does_not_advance() -> None:
    """Invalid validation triggers follow-up without advancing."""
    survey = survey_from_dict(
        {
            "id": "s1",
            "title": "t",
            "questions": [{"id": "q1", "text": "Your name?", "type": "free_text"}],
        }
    )
    engine = MagicMock()
    engine.parse_answer.return_value = {"value": "", "confidence": 0.1}
    engine.validate_answer.return_value = {"valid": False, "issues": ["empty"]}
    engine.suggest_followup.return_value = "Please provide a non-empty name."

    sess = SurveyChatSession(survey=survey, engine=engine)
    r = sess.submit_user_text("   ")
    assert r["status"] == "needs_clarification"
    assert sess.current_question() is not None


def test_adaptive_skip_middle_question() -> None:
    """``next_question_id`` jumps ahead in the survey order."""
    survey = survey_from_dict(
        {
            "id": "s1",
            "title": "t",
            "questions": [
                {"id": "q1", "text": "First?", "type": "free_text", "next_question_id": "q3"},
                {"id": "q2", "text": "Skipped?", "type": "free_text"},
                {"id": "q3", "text": "Third?", "type": "free_text"},
            ],
        }
    )
    engine = MagicMock()
    engine.parse_answer.return_value = {"value": "ok", "confidence": 1.0}
    engine.validate_answer.return_value = {"valid": True, "issues": []}

    sess = SurveyChatSession(survey=survey, engine=engine)
    r1 = sess.submit_user_text("ok")
    assert r1["status"] == "ok"
    assert r1["next_question"]["id"] == "q3"
    assert sess.current_question() is not None
    assert sess.current_question().id == "q3"


def test_adaptive_end_early() -> None:
    """``END_SURVEY_NAV`` finishes after one answer."""
    survey = survey_from_dict(
        {
            "id": "s1",
            "title": "t",
            "questions": [
                {"id": "q1", "text": "Only?", "type": "free_text", "next_question_id": END_SURVEY_NAV},
                {"id": "q2", "text": "Never asked", "type": "free_text"},
            ],
        }
    )
    engine = MagicMock()
    engine.parse_answer.return_value = {"value": "done", "confidence": 1.0}
    engine.validate_answer.return_value = {"valid": True, "issues": []}

    sess = SurveyChatSession(survey=survey, engine=engine)
    r = sess.submit_user_text("done")
    assert r["status"] == "complete"
    assert "q2" not in sess.answers


def test_persistence_called_on_complete() -> None:
    """Optional persistence port receives completed answers."""
    survey = survey_from_dict(
        {
            "id": "s1",
            "title": "t",
            "questions": [{"id": "q1", "text": "?", "type": "free_text"}],
        }
    )
    engine = MagicMock()
    engine.parse_answer.return_value = {"value": "x", "confidence": 1.0}
    engine.validate_answer.return_value = {"valid": True, "issues": []}

    store = MagicMock()
    sess = SurveyChatSession(survey=survey, engine=engine, persistence=store)
    sess.submit_user_text("x")
    store.save_completed.assert_called_once()
    kwargs = store.save_completed.call_args.kwargs
    assert kwargs["survey_id"] == "s1"
    assert kwargs["answers"] == {"q1": "x"}
