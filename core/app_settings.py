"""Application settings persisted for the GUI (scrape options)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "configs" / "app_settings.json"

DEFAULTS = {
    "download_product_images": False,
}


def load_app_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULTS)
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return dict(DEFAULTS)
    return {**DEFAULTS, **data}


def save_app_settings(updates: dict) -> None:
    payload = load_app_settings()
    payload.update(updates)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def download_product_images_enabled() -> bool:
    return bool(load_app_settings().get("download_product_images"))
