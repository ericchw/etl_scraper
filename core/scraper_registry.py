"""Load per-source scraper configuration."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRAPERS_DIR = ROOT / "configs" / "scrapers"


def load_scraper_config(source: str) -> dict:
    path = SCRAPERS_DIR / f"{source}.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def list_sources() -> list[str]:
    if not SCRAPERS_DIR.exists():
        return []
    return sorted(p.stem for p in SCRAPERS_DIR.glob("*.json"))
