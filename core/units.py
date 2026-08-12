"""Normalize dimensions and weight to internal standard (in, lb)."""

from __future__ import annotations

import re
from typing import Any


def _num(text: str) -> float | None:
    match = re.search(r"[\d.]+", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def length_to_in(value: Any, unit_hint: str = "") -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    n = _num(text)
    if n is None:
        return ""
    if "inch" in text or '"' in text or unit_hint in ("in", "inch"):
        return f"{n:.2f}"
    if "centimet" in text or "centimeter" in text or unit_hint in ("cm", "centimeter"):
        return f"{n / 2.54:.2f}"
    if "mm" in text or unit_hint == "mm":
        return f"{n / 25.4:.2f}"
    if "metre" in text or "meter" in text:
        return f"{n * 39.3701:.2f}"
    return f"{n:.2f}"

def weight_to_lb(value: Any, unit_hint: str = "") -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    n = _num(text)
    if n is None:
        return ""
    if "pound" in text or " lb" in text or unit_hint in ("lb", "pound"):
        return f"{n:.2f}"
    if "kilogram" in text or " kg" in text or unit_hint in ("kg", "kilogram"):
        return f"{n * 2.20462:.2f}"
    if ("gram" in text or re.search(r"(?:^|\s)g(?:$|\s)", text)) and "kilogram" not in text:
        return f"{n * 0.00220462:.2f}"
    return f"{n:.2f}"

