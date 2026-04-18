"""FastAPI application: Meta webhook verify + inbound messages → survey replies."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from survey_system.adapters.persistence.memory import InMemoryResponseStore
from survey_system.ai.engine import SurveyAIEngine
from survey_system.ai.groq_client import GroqClient
from survey_system.config import Settings, get_settings
from survey_system.logger import configure_logging, get_logger
from survey_system.whatsapp.incoming import parse_incoming_text_messages
from survey_system.whatsapp.orchestrator import WhatsAppSurveyOrchestrator
from survey_system.whatsapp.security import verify_meta_webhook_signature
from survey_system.whatsapp.sender import MetaWhatsAppSender
from survey_system.whatsapp.survey_payload import load_whatsapp_survey_payload

logger = get_logger(__name__)

# Shown when someone opens /webhook/whatsapp in a browser (no Meta query params).
_WHATSAPP_BROWSER_HELP_HTML = """<!DOCTYPE html>
<html lang="hi"><head><meta charset="utf-8"/><title>WhatsApp webhook</title>
<style>body{font-family:system-ui,sans-serif;max-width:42rem;margin:2rem auto;padding:0 1rem;line-height:1.5;}
code{background:#f4f4f5;padding:0.15rem 0.35rem;border-radius:4px;} .warn{color:#b45309;}</style></head><body>
<h1>WhatsApp webhook yahan hai</h1>
<p class="warn"><strong>DNS_PROBE_FINISHED_NXDOMAIN</strong> ka matlab: jo URL tumne browser mein likha,
uska <strong>domain Internet par maujood nahi</strong> (galat spelling, placeholder, ya purana ngrok URL).</p>
<p><strong>Sahi test:</strong></p>
<ol>
<li>Pehle server chalao: <code>python -m survey_system.whatsapp_server</code></li>
<li>Local check (same PC): <a href="http://127.0.0.1:8080/health"><code>http://127.0.0.1:8080/health</code></a> — yahan <code>{"status":"ok"}</code> aana chahiye.
<strong>Kabhi bhi <code>http://0.0.0.0:8080</code> browser mein mat likho</strong> — <code>ERR_ADDRESS_INVALID</code> aata hai.</li>
<li>Meta ke liye public HTTPS: terminal mein <code>ngrok http 8080</code> chalao, jo <strong>https://….ngrok-free.app</strong> mile
<strong>wahi poora copy</strong> karo + path: <code>/webhook/whatsapp</code></li>
<li>Meta dashboard mein Callback URL mein <strong>HTTPS</strong> URL paste karo — browser mein random domain mat kholo.</li>
</ol>
<p>Project doc: <code>docs/WHATSAPP_SETUP.md</code></p>
</body></html>"""


def create_whatsapp_app(settings: Settings | None = None) -> FastAPI:
    """Build FastAPI app wired to :class:`~survey_system.whatsapp.orchestrator.WhatsAppSurveyOrchestrator`.

    Args:
        settings: Optional settings (defaults to :func:`~survey_system.config.get_settings`).

    Returns:
        Configured FastAPI instance (mount at ``/webhook/whatsapp``).
    """
    s = settings or get_settings()
    configure_logging(s)

    survey_payload = load_whatsapp_survey_payload(s)
    client = GroqClient(
        api_key=s.groq_api_key or "",
        model=s.groq_model,
        proxy=s.https_proxy or None,
    )
    engine = SurveyAIEngine(client)
    persistence = InMemoryResponseStore()
    orchestrator = WhatsAppSurveyOrchestrator(
        survey_payload,
        engine,
        persistence=persistence,
    )
    sender = MetaWhatsAppSender(s)

    app = FastAPI(title="Survey System — WhatsApp Webhook", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/webhook/whatsapp")
    async def verify_webhook(request: Request) -> Response:
        """Meta subscription verification (GET), or a help page if opened in a browser."""
        q = request.query_params
        mode = q.get("hub.mode")
        token = q.get("hub.verify_token")
        challenge = q.get("hub.challenge", "")
        expected = (s.whatsapp_verify_token or "").strip()

        # Not a Meta handshake — user probably pasted /webhook/whatsapp in the browser.
        if not mode and not token and not challenge:
            return Response(
                content=_WHATSAPP_BROWSER_HELP_HTML,
                media_type="text/html; charset=utf-8",
            )

        if not expected:
            raise HTTPException(
                status_code=503,
                detail="WHATSAPP_VERIFY_TOKEN not configured — set in .env and restart.",
            )
        if mode == "subscribe" and token == expected and challenge:
            return Response(content=challenge, media_type="text/plain")
        raise HTTPException(status_code=403, detail="verification failed")

    @app.post("/webhook/whatsapp")
    async def receive_webhook(request: Request) -> dict[str, Any]:
        """Inbound messages (POST)."""
        raw = await request.body()
        if (s.whatsapp_app_secret or "").strip():
            sig = request.headers.get("X-Hub-Signature-256")
            if not verify_meta_webhook_signature(s.whatsapp_app_secret, sig, raw):
                raise HTTPException(status_code=403, detail="bad_signature")

        try:
            body = json.loads(raw.decode("utf-8") if raw else "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid json") from exc

        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="json must be object")

        incoming = parse_incoming_text_messages(body)
        if not incoming:
            return {"ok": True}

        if not sender.is_configured:
            logger.warning(
                "whatsapp_incoming_but_sender_not_configured",
                extra={"hint": "Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID"},
            )
            return {"ok": True}

        for msg in incoming:
            chunks = await run_in_threadpool(
                orchestrator.handle_message,
                msg.wa_from_id,
                msg.body,
            )
            for part in chunks:
                await run_in_threadpool(sender.send_text, msg.wa_from_id, part)

        return {"ok": True}

    return app
