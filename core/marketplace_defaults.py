"""Shared marketplace defaults (discount dates, etc.)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS_PATH = ROOT / "configs" / "marketplace_defaults.json"

DEFAULT_BESTBUY = {
    "discount_start_date": "",
    "discount_end_date": "",
    # "discount_duration_days": 30,
}


def load_defaults() -> dict:
    if not DEFAULTS_PATH.exists():
        return {"bestbuy": dict(DEFAULT_BESTBUY)}
    with open(DEFAULTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"bestbuy": dict(DEFAULT_BESTBUY)}
    bb = data.get("bestbuy") if isinstance(data.get("bestbuy"), dict) else {}
    return {
        "bestbuy": {
            **DEFAULT_BESTBUY,
            **bb,
        },
    }


def save_defaults(bestbuy: dict) -> None:
    payload = load_defaults()
    payload["bestbuy"] = {**payload.get("bestbuy", {}), **bestbuy}
    DEFAULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFAULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def bestbuy_discount_dates() -> tuple[str, str]:
    """
    Return (start, end) as yyyy-MM-dd.

    Empty config start → today. Empty end → start + discount_duration_days.
    """
    bb = load_defaults().get("bestbuy") or {}
    start_s = str(bb.get("discount_start_date") or "").strip()
    end_s = str(bb.get("discount_end_date") or "").strip()
    # duration = int(bb.get("discount_duration_days") or 30)

    if start_s:
        start = date.fromisoformat(start_s)
    else:
        start = date.today()
        start_s = start.isoformat()

    if end_s:
        end = date.fromisoformat(end_s)
    # else:
    #     end = start + timedelta(days=duration)
    #     end_s = end.isoformat()

    return start_s, end_s
