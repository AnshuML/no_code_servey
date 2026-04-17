"""Streamlit POC UI for chat-based AI-assisted surveys."""

from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any

import streamlit as st

from survey_system.adapters.persistence.memory import InMemoryResponseStore
from survey_system.ai.engine import SurveyAIEngine
from survey_system.ai.groq_client import GroqClient
from survey_system.chat.session import SurveyChatSession
from survey_system.config import Settings, get_settings
from survey_system.logger import configure_logging, get_logger
from survey_system.schema.survey import survey_from_dict
from survey_system.survey_builder.builder import build_survey_from_prompt

logger = get_logger(__name__)

_ACTIVE_SURVEY_KEY = "active_survey_dict"
_RESPONSE_STORE_KEY = "response_store_singleton"
_LAST_AUDIO_VOICE_KEY = "last_voice_question_digest"


def _pretty_field_label(key: str) -> str:
    """Turn keys like ``name-1`` or ``primary-language-9`` into readable labels."""
    m = re.match(r"^(.*)-(\d+)$", str(key))
    raw = m.group(1) if m else str(key)
    return raw.replace("-", " ").replace("_", " ").strip().title()


def _answer_sort_key(key: str) -> tuple[int, str]:
    """Sort by trailing ``-N`` when present, else by key string."""
    m = re.match(r"^.*-(\d+)$", str(key))
    n = int(m.group(1)) if m else 0
    return (n, str(key))


def _format_display_value(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _render_completion_form(answers: dict[str, Any]) -> None:
    """Render answers as a read-only filled form (paper-like)."""
    st.markdown(
        '<p class="form-sheet-title">Recorded responses — jaise form fill kiya ho</p>',
        unsafe_allow_html=True,
    )
    keys = sorted(answers.keys(), key=_answer_sort_key)
    with st.container(border=True):
        for i, k in enumerate(keys):
            label = _pretty_field_label(k)
            val = _format_display_value(answers[k])
            wid = f"summary_field_{i}_{abs(hash(str(k))) % 10_000_000}"
            if len(val) > 120 or "\n" in val:
                st.text_area(
                    label,
                    value=val,
                    height=min(320, max(90, 24 + val.count("\n") * 22)),
                    disabled=True,
                    key=wid,
                )
            else:
                st.text_input(label, value=val, disabled=True, key=wid)

    with st.expander("Raw JSON (technical)", expanded=False):
        st.json(answers)

_FAMILY_SURVEY: dict[str, Any] = {
    "schema_version": "1.0",
    "id": "family_survey_hindi",
    "title": "Parivar / Family survey",
    "questions": [
        {
            "id": "total_members",
            "text": (
                "Aapki family mein kul kitne log hain? "
                "(Khud ko bhi giniye — number bataiye.)"
            ),
            "type": "number",
            "required": True,
            "min_value": 1,
            "max_value": 30,
        },
        {
            "id": "monthly_income_inr",
            "text": (
                "Ghar ki kul monthly income lagbhag kitni hai? "
                "Sirf number bataiye (₹ — Indian Rupees)."
            ),
            "type": "number",
            "required": True,
            "min_value": 0,
            "max_value": 100000000,
        },
        {
            "id": "father_name",
            "text": "Pita ji (father) ka poora naam kya hai?",
            "type": "free_text",
            "required": True,
        },
        {
            "id": "father_occupation",
            "text": "Pita ji kya kaam karte hain? (naukri, business, kheti, retired, etc.)",
            "type": "free_text",
            "required": True,
        },
        {
            "id": "mother_name",
            "text": "Mata ji (mother) ka poora naam kya hai?",
            "type": "free_text",
            "required": True,
        },
        {
            "id": "mother_occupation",
            "text": "Mata ji kya karti hain? (naukri, ghar sambhalna, business, etc.)",
            "type": "free_text",
            "required": True,
        },
        {
            "id": "members_detail",
            "text": (
                "Har family member ke baare mein likhiye: naam, ladka hai ya ladki, "
                "aur wo kya karte hain (padhai, kaam, chhota bachcha, etc.). "
                "Ek line mein ek member — jitne members bataye, sab cover karein."
            ),
            "type": "free_text",
            "required": True,
        },
        {
            "id": "consent",
            "text": (
                "Kya aap ye parivar survey poora karne ke liye sahmat hain "
                "aur jo jawab diye hain wo sahi maan sakte hain?"
            ),
            "type": "yes_no",
            "required": True,
        },
    ],
}


def _inject_styles() -> None:
    """Inject global CSS tuned for Streamlit dark theme (see .streamlit/config.toml)."""
    st.markdown(
        """
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');

  html, body, [class*="stApp"] {
    font-family: 'DM Sans', system-ui, sans-serif;
  }
  .block-container {
    padding-top: 1.25rem !important;
    padding-bottom: 3rem !important;
    max-width: 920px !important;
  }
  footer {visibility: hidden;}
  .stDeployButton {display: none;}

  /* Main area subtle depth on dark bg */
  [data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse 120% 80% at 50% -20%, #1e293b 0%, #0b1220 45%) !important;
  }

  .survey-hero {
    background: linear-gradient(135deg, #0c4a6e 0%, #134e4a 40%, #0f766e 100%);
    border-radius: 20px;
    padding: 1.75rem 1.5rem 1.5rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.45);
    border: 1px solid rgba(45, 212, 191, 0.25);
    color: #f8fafc;
  }
  .survey-hero h1 {
    font-size: 1.65rem !important;
    font-weight: 700 !important;
    margin: 0 0 0.35rem 0 !important;
    letter-spacing: -0.02em;
    color: #f8fafc !important;
  }
  .survey-hero .sub {
    opacity: 0.88;
    font-size: 0.95rem;
    margin: 0;
    color: #cbd5e1 !important;
  }
  .badge {
    display: inline-block;
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(8px);
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    color: #99f6e4 !important;
    border: 1px solid rgba(45, 212, 191, 0.35);
  }

  .question-card {
    background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 1.35rem 1.25rem;
    margin: 1rem 0 1.25rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
  }
  .question-card .q-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #2dd4bf;
    margin-bottom: 0.5rem;
  }
  .question-card .q-text {
    font-size: 1.08rem;
    line-height: 1.55;
    color: #f1f5f9;
    font-weight: 500;
  }
  .meta-pill {
    display: inline-block;
    margin-top: 0.85rem;
    font-size: 0.78rem;
    color: #94a3b8;
    background: #0f172a;
    border: 1px solid #334155;
    padding: 0.2rem 0.55rem;
    border-radius: 8px;
  }

  .success-panel {
    background: linear-gradient(135deg, #064e3b 0%, #022c22 100%);
    border: 1px solid #059669;
    border-radius: 16px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
  }
  .success-panel h2 {
    margin: 0 0 0.5rem 0;
    color: #a7f3d0;
    font-size: 1.35rem;
  }
  .success-panel p {
    color: #6ee7b7 !important;
  }

  div[data-testid="stSidebarContent"] {
    background: linear-gradient(180deg, #111827 0%, #0b1220 100%) !important;
    padding-top: 0.5rem;
    border-right: 1px solid #1e293b !important;
  }
  .sidebar-section-title {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #94a3b8;
    margin: 1rem 0 0.5rem 0;
  }

  /* Progress bar: teal track */
  [data-testid="stProgressBar"] > div {
    background-color: rgba(45, 212, 191, 0.25) !important;
  }

  .form-sheet-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0 0 0.75rem 0;
  }
  [data-testid="stTextInput"] input[disabled],
  [data-testid="stTextArea"] textarea[disabled] {
    -webkit-text-fill-color: #f1f5f9 !important;
    color: #f1f5f9 !important;
    opacity: 1 !important;
  }
</style>
        """,
        unsafe_allow_html=True,
    )


def _init_session_state() -> None:
    """Initialize Streamlit session state keys once."""
    if "survey_session" not in st.session_state:
        st.session_state.survey_session = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if _ACTIVE_SURVEY_KEY not in st.session_state:
        st.session_state[_ACTIVE_SURVEY_KEY] = None
    if _RESPONSE_STORE_KEY not in st.session_state:
        st.session_state[_RESPONSE_STORE_KEY] = InMemoryResponseStore()
    if _LAST_AUDIO_VOICE_KEY not in st.session_state:
        st.session_state[_LAST_AUDIO_VOICE_KEY] = None


def _active_survey_payload() -> dict[str, Any]:
    """Return the JSON dict for the survey currently in use (prompt-built or family demo)."""
    custom = st.session_state.get(_ACTIVE_SURVEY_KEY)
    if custom is None:
        return _FAMILY_SURVEY
    return custom


def _groq_client(settings: Settings) -> GroqClient:
    """Build a Groq client using optional ``HTTPS_PROXY`` from settings."""
    proxy = settings.https_proxy or None
    return GroqClient(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        proxy=proxy,
    )


def _make_chat_session(payload: dict[str, Any]) -> SurveyChatSession | None:
    """Create a chat session from a survey dict."""
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    survey = survey_from_dict(payload)
    client = _groq_client(settings)
    engine = SurveyAIEngine(client)
    store: InMemoryResponseStore = st.session_state[_RESPONSE_STORE_KEY]
    return SurveyChatSession(survey=survey, engine=engine, persistence=store)


def _clear_survey_progress() -> None:
    """Clear chat history and invalidate session (same survey / new survey)."""
    st.session_state.messages = []
    st.session_state.survey_session = None
    st.session_state[_LAST_AUDIO_VOICE_KEY] = None


@st.cache_resource(show_spinner="Loading local Whisper model…")
def _cached_whisper_stt(model_size: str, device: str, compute_type: str):
    """Open-source STT (faster-whisper); cached for the Streamlit process."""
    from survey_system.adapters.speech.faster_whisper_stt import FasterWhisperSpeechToText

    return FasterWhisperSpeechToText(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
    )


def _handle_submitted_text(
    sess: SurveyChatSession,
    prompt: str,
    *,
    display_text: str | None = None,
) -> bool:
    """Append messages, submit answer. Return True if caller should ``st.rerun()`` (complete)."""
    shown = display_text if display_text is not None else prompt
    st.session_state.messages.append({"role": "user", "content": shown})
    with st.chat_message("user", avatar="🙂"):
        st.write(shown)

    result = sess.submit_user_text(prompt)
    logger.info("streamlit_turn_result", status=result.get("status"))

    if result["status"] == "complete":
        msg = "Sab sawal complete — thank you! Neeche filled form summary dekho."
        st.session_state.messages.append({"role": "assistant", "content": msg})
        with st.chat_message("assistant", avatar="✨"):
            st.write(msg)
        return True

    if result["status"] == "ok":
        nxt = result.get("next_question") or {}
        msg = f"Recorded. Next: {nxt.get('text', '')}"
        st.session_state.messages.append({"role": "assistant", "content": msg})
        with st.chat_message("assistant", avatar="✨"):
            st.write(msg)
        return False

    if result["status"] == "needs_clarification":
        msg = result.get("follow_up", "Please clarify your answer.")
        st.session_state.messages.append({"role": "assistant", "content": msg})
        with st.chat_message("assistant", avatar="✨"):
            st.write(msg)
        return False

    msg = "Something went wrong parsing your answer. Please try again."
    st.session_state.messages.append({"role": "assistant", "content": msg})
    with st.chat_message("assistant", avatar="✨"):
        st.write(msg)
    return False


def _try_render_voice_answer(settings: Settings, sess: SurveyChatSession) -> bool:
    """Transcribe new audio (if any) and submit. Returns True when survey just completed."""
    if not hasattr(st, "audio_input"):
        st.caption(
            "Voice: Streamlit 1.34+ chahiye — `pip install -U streamlit`."
        )
        return False

    q_active = sess.current_question()
    if q_active is None:
        return False

    audio = st.audio_input(
        "🎤 Voice jawab (optional — local Whisper)",
        key="survey_voice_answer",
    )
    if audio is None:
        return False

    try:
        stt = _cached_whisper_stt(
            settings.whisper_model_size,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
    except ImportError:
        st.info(
            'Local open-source STT: `pip install -e ".[voice]"` (faster-whisper), phir refresh.'
        )
        return False
    except Exception as exc:
        logger.exception("whisper_model_load_failed")
        st.warning(f"Speech model load nahi ho paya: {exc}")
        return False

    raw: bytes
    if isinstance(audio, (bytes, bytearray)):
        raw = bytes(audio)
    else:
        raw = audio.getvalue()

    digest = hashlib.sha256(raw).hexdigest()
    voice_mark = (q_active.id, digest)
    if voice_mark == st.session_state.get(_LAST_AUDIO_VOICE_KEY):
        return False

    with st.spinner("Speech → text (local Whisper)…"):
        lang = (settings.whisper_language or "").strip() or None
        try:
            text = stt.transcribe(raw, language_hint=lang)
        except Exception as exc:
            logger.exception("whisper_transcribe_failed")
            st.error(f"Transcribe fail: {exc}")
            return False

    if not text.strip():
        st.warning("Kuch text nahi mila — dubara record karo.")
        st.session_state[_LAST_AUDIO_VOICE_KEY] = voice_mark
        return False

    st.session_state[_LAST_AUDIO_VOICE_KEY] = voice_mark
    display = f"🎤 {text}"
    return _handle_submitted_text(sess, text, display_text=display)


def _question_position(payload: dict[str, Any], question_id: str) -> tuple[int, int]:
    """Return (1-based index, total) for the current question id."""
    ids = [q["id"] for q in payload.get("questions", [])]
    try:
        idx = ids.index(question_id) + 1
    except ValueError:
        idx = 1
    total = len(ids) or 1
    return idx, total


def main() -> None:
    """Streamlit entrypoint."""
    settings = get_settings()
    configure_logging(settings)

    st.set_page_config(
        page_title="AI Survey Studio",
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="📋",
    )
    _inject_styles()
    _init_session_state()

    with st.sidebar:
        st.markdown(
            '<p class="sidebar-section-title">Samajhna zaroori</p>',
            unsafe_allow_html=True,
        )
        st.info(
            "**Chat** = sirf **us sawal** ka jawab jo screen par hai.\n\n"
            "**Naya survey** = neeche prompt likho, phir **Generate**."
        )

        st.markdown(
            '<p class="sidebar-section-title">Voice (optional)</p>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Main area → **Voice se survey — quick demo** expander. "
            "Setup: `pip install -e \".[voice]\"` phir app refresh."
        )

        st.markdown(
            '<p class="sidebar-section-title">A) Parivar demo</p>',
            unsafe_allow_html=True,
        )
        if st.button("Parivar survey load / reset", use_container_width=True):
            st.session_state[_ACTIVE_SURVEY_KEY] = None
            _clear_survey_progress()
            st.rerun()

        st.markdown(
            '<p class="sidebar-section-title">B) AI se survey design</p>',
            unsafe_allow_html=True,
        )
        st.caption("DNS error? Internet / `HTTPS_PROXY` check karein.")
        prompt_for_builder = st.text_area(
            "Survey ka goal (English ya Hindi)",
            placeholder=(
                "Example: Rural households — employment, daily wages, "
                "work type, seasonal unemployment."
            ),
            height=150,
            key="survey_builder_prompt",
            label_visibility="collapsed",
        )
        if st.button(
            "Survey generate & start",
            type="primary",
            use_container_width=True,
        ):
            if not prompt_for_builder.strip():
                st.error("Pehle prompt likho.")
            elif not settings.groq_api_key:
                st.error("GROQ_API_KEY chahiye.")
            else:
                try:
                    client = _groq_client(settings)
                    built = build_survey_from_prompt(
                        client,
                        prompt_for_builder.strip(),
                    )
                    st.session_state[_ACTIVE_SURVEY_KEY] = built.model_dump(mode="json")
                    _clear_survey_progress()
                    st.success(f"Ready: **{built.title}**")
                    st.rerun()
                except Exception as exc:
                    logger.exception("survey_build_failed")
                    st.error(f"Survey nahi ban paya: {exc}")

        st.divider()
        if st.button("Chat clear (same survey)", use_container_width=True):
            _clear_survey_progress()
            st.rerun()

    if st.session_state.survey_session is None:
        st.session_state.survey_session = _make_chat_session(_active_survey_payload())

    sess = st.session_state.survey_session
    if sess is None:
        st.warning(
            "Set `GROQ_API_KEY` in your environment or `.env`, then refresh this page."
        )
        logger.warning("streamlit_missing_groq_key")
        return

    payload = _active_survey_payload()
    title = html.escape(str(payload.get("title", "Survey")))
    is_custom = bool(st.session_state.get(_ACTIVE_SURVEY_KEY))
    badge = "AI-generated" if is_custom else "Family demo"

    st.markdown(
        f"""
<div class="survey-hero">
  <span class="badge">{badge}</span>
  <h1>{title}</h1>
  <p class="sub">Groq LLM · voice (local Whisper) · typed chat · smart validation</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    q = sess.current_question()
    if q is None:
        st.balloons()
        st.markdown(
            """
<div class="success-panel">
  <h2>Survey complete — thank you</h2>
  <p style="margin:0;">Neeche recorded answers — form jaisa view.</p>
</div>
            """,
            unsafe_allow_html=True,
        )
        _render_completion_form(sess.answers)
        return

    idx, total = _question_position(payload, q.id)
    prog = idx / float(total)
    c1, c2 = st.columns([4, 1])
    with c1:
        st.progress(prog)
        st.caption(f"**Question {idx}** of {total}")
    with c2:
        st.caption(f"type: `{html.escape(q.type.value)}`")

    q_safe = html.escape(q.text)
    st.markdown(
        f"""
<div class="question-card">
  <div class="q-label">Current question</div>
  <div class="q-text">{q_safe}</div>
  <span class="meta-pill">id: {html.escape(q.id)}</span>
</div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🎤 Voice se survey — quick demo (kaise karein)", expanded=False):
        st.markdown(
            """
**Ek baar setup (CMD / terminal, project folder se)**  
```text
pip install -e ".[voice]"
```
Phir Streamlit dubara chalao. Optional: `.env` mein `SURVEY_WHISPER_LANGUAGE=hi` (Hindi bias ke liye).

---

**Har sawal par — ye flow follow karo**

1. **Upar wala sawal padho** — chat sirf *us* sawal ka jawab hai.  
2. **Neeche scroll** — pehle purana chat, phir **“Voice jawab (local Whisper)”** dikhega.  
3. **Mic dabao, bol ke roko** — recording save hote hi app **local Whisper** se text banata hai (internet sirf Groq validation ke liye).  
4. **Chat mein `🎤 …` line dikhegi** = tumhara voice answer; agla sawal ya clarification wahi aa jayega jaise type karne par.  
5. **Chaho to type bhi kar sakte ho** — dono mix: kabhi voice, kabhi keyboard.

---

**Demo script (Parivar pe try karo)**  
Pehle sawal *members count* — mic se bolo: *“Hamare ghar mein paanch log hain”*  
Income wale par: *“pachaas hazaar”*  
Free-text wale par 1–2 short vaakya Hindi mein.

---

**Agar voice dikhe hi nahi**  
Streamlit `>=1.34` hona chahiye; warna upgrade: `pip install -U "streamlit>=1.34"`.
            """
        )

    for m in st.session_state.messages:
        av = "🙂" if m["role"] == "user" else "✨"
        with st.chat_message(m["role"], avatar=av):
            st.write(m["content"])

    if _try_render_voice_answer(settings, sess):
        st.rerun()

    if prompt := st.chat_input("Yahan apna jawab likho…"):
        if _handle_submitted_text(sess, prompt):
            st.rerun()


if __name__ == "__main__":
    main()
