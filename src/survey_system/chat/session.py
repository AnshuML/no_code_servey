"""Stateful chat session over a :class:`~survey_system.schema.survey.Survey`."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from survey_system.ai.engine import SurveyAIEngine
from survey_system.exceptions import LLMError, SurveySessionError
from survey_system.logger import get_logger
from survey_system.ports.persistence import ResponsePersistence
from survey_system.schema.survey import END_SURVEY_NAV, Question, Survey
from survey_system.validation.pipeline import validate_rules

logger = get_logger(__name__)


@dataclass
class SurveyChatSession:
    """Tracks progress, answers, and AI-assisted validation for a survey."""

    survey: Survey
    engine: SurveyAIEngine
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    persistence: ResponsePersistence | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    transcript: list[dict[str, Any]] = field(default_factory=list)
    _active_question_id: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.survey.questions:
            self._active_question_id = self.survey.questions[0].id
        else:
            self._active_question_id = None

    def _by_id(self) -> dict[str, Question]:
        return {q.id: q for q in self.survey.questions}

    def _order_index(self) -> dict[str, int]:
        return {q.id: i for i, q in enumerate(self.survey.questions)}

    def _next_question_after(self, q: Question) -> Question | None:
        """Resolve adaptive ``next_question_id`` or linear survey order."""
        nxt = q.next_question_id
        if nxt == END_SURVEY_NAV:
            return None
        if nxt is not None:
            return self._by_id()[nxt]
        idx = self._order_index()[q.id]
        if idx + 1 >= len(self.survey.questions):
            return None
        return self.survey.questions[idx + 1]

    def _persist_completed(self) -> None:
        if self.persistence is None:
            return
        self.persistence.save_completed(
            survey_id=self.survey.id,
            session_id=self.session_id,
            answers=dict(self.answers),
            transcript=list(self.transcript),
        )

    def current_question(self) -> Question | None:
        """Return the active question, or ``None`` if finished.

        Returns:
            Next question to ask, if any.
        """
        if self._active_question_id is None:
            return None
        return self._by_id()[self._active_question_id]

    def is_complete(self) -> bool:
        """Return True when all questions are answered."""
        return self.current_question() is None

    def submit_user_text(self, text: str) -> dict[str, Any]:
        """Parse and validate an answer for the current question.

        Args:
            text: Raw user message for the active question.

        Returns:
            Result dict with keys: ``status`` (``ok``|``needs_clarification``|``complete``|``error``),
            and optional ``follow_up``, ``parsed``, ``issues``.

        Raises:
            SurveySessionError: If called when the survey is already complete.
        """
        q = self.current_question()
        if q is None:
            raise SurveySessionError(
                "no active question; survey is complete",
                details={"survey_id": self.survey.id},
            )

        self.transcript.append({"role": "user", "text": text, "question_id": q.id})
        logger.info(
            "survey_answer_received",
            survey_id=self.survey.id,
            question_id=q.id,
            text_len=len(text),
        )

        try:
            parsed = self.engine.parse_answer(q, text)
        except LLMError as exc:
            logger.warning("survey_parse_failed", question_id=q.id, error=str(exc))
            self.transcript.append(
                {"role": "assistant", "text": "I could not parse that answer. Please try again."}
            )
            return {
                "status": "error",
                "message": "parse_failed",
                "issues": [str(exc)],
            }

        value = parsed.get("value")
        rules = validate_rules(q, value)
        try:
            llm_val = self.engine.validate_answer(q, {"value": value, **parsed})
        except LLMError as exc:
            logger.warning("survey_validate_failed", question_id=q.id, error=str(exc))
            llm_val = {"valid": False, "issues": []}

        llm_ok = bool(llm_val.get("valid", False))
        rules_ok = rules.valid

        if rules_ok and llm_ok:
            self.answers[q.id] = value
            nxt = self._next_question_after(q)
            self._active_question_id = nxt.id if nxt else None
            self.transcript.append(
                {
                    "role": "assistant",
                    "text": "Recorded.",
                    "question_id": q.id,
                    "parsed": parsed,
                }
            )
            if nxt is None:
                self._persist_completed()
                return {"status": "complete", "parsed": parsed, "answers": dict(self.answers)}
            return {
                "status": "ok",
                "parsed": parsed,
                "next_question": {"id": nxt.id, "text": nxt.text, "type": nxt.type.value},
            }

        issues = list(rules.issues)
        if isinstance(llm_val.get("issues"), list):
            issues.extend(str(x) for x in llm_val["issues"])

        try:
            follow = self.engine.suggest_followup(q, {"value": value, **parsed}, llm_val)
        except LLMError as exc:
            logger.warning("survey_followup_failed", question_id=q.id, error=str(exc))
            follow = "Could you clarify your answer?"

        self.transcript.append({"role": "assistant", "text": follow})
        return {
            "status": "needs_clarification",
            "issues": issues,
            "follow_up": follow,
            "parsed": parsed,
        }
