"""Parse B&H feature/design from cached raw JSON (mirrors page JS helpers)."""

from __future__ import annotations


def parse_features_from_raw(raw: dict) -> list[str]:
    """Same output as BH_GET_FEATURES_JS (list of strings)."""
    feats = raw.get("features")
    if isinstance(feats, list):
        return [str(f).strip() for f in feats if str(f).strip()]
    if isinstance(feats, str) and feats.strip():
        return [line.strip() for line in feats.splitlines() if line.strip()]
    return []


def parse_description_from_raw(raw: dict) -> str:
    """Same output as BH_GET_DESIGN_JS (plain text, newlines preserved)."""
    return str(raw.get("description") or "").replace("\r\n", "\n").replace("\r", "\n")
