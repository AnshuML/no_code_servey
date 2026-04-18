# no_code_servey

AI-assisted **no-code survey** POC: natural-language survey design, chat (or voice) answers, Groq LLM validation, Streamlit UI.

## Quick start

```bash
pip install -e .
pip install -r requirements-voice.txt   # optional: local Whisper
cp .env.example .env                    # add GROQ_API_KEY
python -m streamlit run src/survey_system/streamlit_app.py
```

**WhatsApp (Meta Cloud API):** `python -m survey_system.whatsapp_server` then configure webhook (HTTPS). Full steps: `docs/WHATSAPP_SETUP.md`.

See `docs/ARCHITECTURE.md` for layout (ports/adapters, POC → production).

## License

Add your license here if applicable.
