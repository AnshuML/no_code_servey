"""Resolve survey JSON for the WhatsApp channel (generic: file or default demo)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from survey_system.config import Settings
from survey_system.demodata.family_survey import FAMILY_SURVEY_PAYLOAD


def load_whatsapp_survey_payload(settings: Settings) -> dict[str, Any]:
    """Return a fresh dict suitable for ``survey_from_dict`` (deep-copied)."""
    path_str = (settings.whatsapp_survey_json_path or "").strip()
    if path_str:
        path = Path(path_str)
        if not path.is_file():
            raise FileNotFoundError(f"WHATSAPP_SURVEY_JSON not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Survey JSON root must be an object")
        return copy.deepcopy(data)
    return copy.deepcopy(FAMILY_SURVEY_PAYLOAD)
