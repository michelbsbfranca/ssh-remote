"""Preferências persistentes da interface (ex.: tema claro/escuro)."""
from __future__ import annotations

import json

from . import crypto

PREFERENCES_FILE = crypto.CONFIG_DIR / "preferences.json"

DEFAULTS = {"dark_mode": True}


def load() -> dict:
    crypto._ensure_config_dir()
    if not PREFERENCES_FILE.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save(preferences: dict) -> None:
    crypto._ensure_config_dir()
    PREFERENCES_FILE.write_text(json.dumps(preferences, indent=2), encoding="utf-8")
