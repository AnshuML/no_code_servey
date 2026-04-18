"""One ``SurveyChatSession`` per WhatsApp user id (``from``) — generic multi-respondent."""

from __future__ import annotations

import copy
import threading
import uuid
from typing import Any

from survey_system.ai.engine import SurveyAIEngine
from survey_system.chat.session import SurveyChatSession
from survey_system.ports.persistence import ResponsePersistence
from survey_system.schema.survey import survey_from_dict

_RESET_TOKENS = frozenset(
    {
        "reset",
        "/reset",
        "restart",
        "/restart",
        "नया",
        "नया सर्वे",
        "new",
        "start over",
    }
)


def _chunk_text(text: str, max_chars: int = 3500) -> list[str]:
    """WhatsApp text body limit is 4096; keep margin."""
    s = text.strip()
    if not s:
        return []
    if len(s) <= max_chars:
        return [s]
    return [s[i : i + max_chars] for i in range(0, len(s), max_chars)]


class WhatsAppSurveyOrchestrator:
    """Isolated survey sessions keyed by WhatsApp ``from`` id (2–3 users or more)."""

    def __init__(
        self,
        survey_template: dict[str, Any],
        engine: SurveyAIEngine,
        persistence: ResponsePersistence | None = None,
    ) -> None:
        self._template = copy.deepcopy(survey_template)
        self._engine = engine
        self._persistence = persistence
        self._sessions: dict[str, SurveyChatSession] = {}
        self._lock = threading.Lock()

    def _new_session(self, wa_id: str) -> SurveyChatSession:
        survey = survey_from_dict(copy.deepcopy(self._template))
        return SurveyChatSession(
            survey=survey,
            engine=self._engine,
            persistence=self._persistence,
            session_id=f"wa_{wa_id}_{uuid.uuid4().hex[:12]}",
        )

    def handle_message(self, wa_id: str, text: str) -> list[str]:
        """Return one or more outbound text chunks for this inbound message."""
        raw = text if text is not None else ""
        stripped = raw.strip()
        with self._lock:
            low = stripped.lower()
            if low in _RESET_TOKENS:
                self._sessions[wa_id] = self._new_session(wa_id)
                return self._opening_lines(self._sessions[wa_id])

            sess = self._sessions.get(wa_id)
            if sess is None or sess.is_complete():
                self._sessions[wa_id] = self._new_session(wa_id)
                sess = self._sessions[wa_id]

            if not stripped:
                return self._opening_lines(sess)

            result = sess.submit_user_text(stripped)
            return self._replies_for_result(wa_id, sess, result)

    def _opening_lines(self, sess: SurveyChatSession) -> list[str]:
        q = sess.current_question()
        if q is None:
            return ["Is survey mein abhi koi sawal nahi hai."]
        intro = (
            "Survey shuru. Har sawal ka jawab bhejiye.\n"
            "Rukne / dubara shuru: RESET likho.\n\n"
            f"*Sawal 1:*\n{q.text}"
        )
        return _chunk_text(intro)

    def _replies_for_result(
        self,
        wa_id: str,
        sess: SurveyChatSession,
        result: dict[str, Any],
    ) -> list[str]:
        status = result.get("status")
        if status == "complete":
            lines = ["Dhanyavaad! Survey *complete*."]
            for k, v in sess.answers.items():
                lines.append(f"• {k}: {v}")
            self._sessions.pop(wa_id, None)
            return _chunk_text("\n".join(lines))

        if status == "ok":
            nxt = result.get("next_question") or {}
            nxt_text = nxt.get("text") or ""
            body = f"✓ Recorded.\n\n*Agla sawal:*\n{nxt_text}"
            return _chunk_text(body)

        if status == "needs_clarification":
            follow = result.get("follow_up", "Jawab thoda clear karein, please.")
            return _chunk_text(str(follow))

        issues = result.get("issues") or []
        msg = result.get("message", "error")
        body = "Abhi jawab save nahi ho paya. Dobara try karein.\n" + "\n".join(
            str(x) for x in issues
        )
        return _chunk_text(f"{body}\n({msg})")
