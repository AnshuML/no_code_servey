# Architecture: POC → production (minimal rework)

This repo follows a **ports-and-adapters** (hexagonal) layout so you can swap infrastructure without rewriting survey logic.

## Layers

| Layer | Role | Examples |
|--------|------|----------|
| **Domain / core** | Survey schema, validation rules, AI engine orchestration | `schema/`, `validation/`, `ai/engine.py` |
| **Application** | One session = one respondent run | `chat/session.py` (`SurveyChatSession`) |
| **Ports** | Interfaces only (Protocols) | `ports/persistence.py`, `ports/speech.py` |
| **Adapters** | Concrete I/O | `adapters/persistence/memory.py`, future `adapters/persistence/sqlite.py` |
| **Delivery** | UI / messaging | `streamlit_app.py` today; future FastAPI + Telegram/Matrix |

## Swap points (production)

1. **Persistence** — Implement `ResponsePersistence` with PostgreSQL/SQLite; keep `InMemoryResponseStore` for tests and demos.
2. **Speech** — `FasterWhisperSpeechToText` implements `SpeechToText` via **faster-whisper** (MIT). Install: `pip install -e ".[voice]"`. Streamlit uses `st.audio_input` → transcribe → same `SurveyChatSession.submit_user_text` path as typed chat. Env: `SURVEY_WHISPER_MODEL`, `SURVEY_WHISPER_DEVICE`, `SURVEY_WHISPER_COMPUTE_TYPE`, `SURVEY_WHISPER_LANGUAGE` (optional).
3. **Channels** — New transport = new adapter that reads/writes text and calls `SurveyChatSession.submit_user_text` (same core).
4. **LLM** — `GroqClient` is isolated in `ai/`; a future **Ollama** / **vLLM** client can sit behind the same `SurveyAIEngine` interface if you extract a narrow protocol (optional follow-up).

## Open-source policy

- Prefer **OSI-approved** libraries and self-hosted components.
- Avoid vendor lock-in at the **port** boundary: business logic must not import Streamlit or a specific DB driver.

## Adaptive surveys

- Each `Question` may set `next_question_id` (or `END_SURVEY_NAV` / `"__END__"` to stop early).
- If unset, the session advances **linearly** in `questions` order.

## Running

- Install: `pip install -e ".[dev]"` from the repo root.
- App: `python -m streamlit run src/survey_system/streamlit_app.py`
