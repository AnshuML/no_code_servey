"""Run WhatsApp webhook server: ``python -m survey_system.whatsapp_server``."""

from __future__ import annotations

import sys

import uvicorn

from survey_system.config import get_settings
from survey_system.logger import configure_logging, get_logger
from survey_system.whatsapp.app import create_whatsapp_app

logger = get_logger(__name__)


def main() -> None:
    """Listen on all interfaces; browsers must use ``127.0.0.1`` or ``localhost``, not ``0.0.0.0``."""
    settings = get_settings()
    configure_logging(settings)
    app = create_whatsapp_app(settings)
    port = 8080
    # 0.0.0.0 = accept connections on every interface (ngrok, LAN). Browsers cannot navigate TO 0.0.0.0.
    print(
        f"\n  Browser test (same PC):  http://127.0.0.1:{port}/health\n"
        f"  Webhook path:            http://127.0.0.1:{port}/webhook/whatsapp\n"
        f"  Do NOT use 0.0.0.0 in the address bar — Chrome/Edge show ERR_ADDRESS_INVALID.\n",
        file=sys.stderr,
    )
    logger.info(
        "whatsapp_server_starting",
        bind="0.0.0.0",
        port=port,
        browser_health_url=f"http://127.0.0.1:{port}/health",
    )
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
