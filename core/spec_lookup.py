"""Read nested retailer spec dicts (fuzzy group/key) and resolve multi-path candidates."""

from __future__ import annotations
import fnmatch
import re
from typing import Any

def spec_value(specs: dict | None, group: str, key: str) -> str:
    """Case-insensitive group and key match."""
    if not isinstance(specs, dict):
        return ""

    target_group = group.strip().lower()
    matched_block: dict = {}
    for g_key, g_val in specs.items():
        if str(g_key).strip().lower() == target_group and isinstance(g_val, dict):
            matched_block = g_val
            break

    if not matched_block:
        return ""

    target_key = key.strip().lower()
    for k, v in matched_block.items():
        if str(k).strip().lower() == target_key:
            value = "" if v is None else str(v).strip()
            return "" if value.lower() == "none" else value

    return ""

def spec_list(
    specs: dict | None,
    group: str,
    key: str,
    *,
    separators: str = r"[,;/|\r\n]"
) -> list[str]:
    value = spec_value(specs, group, key)

    if not value:
        return []

    pattern = re.compile(separators)

    result = []
    buf = []
    depth = 0

    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)

        if depth == 0 and pattern.match(ch):
            item = "".join(buf).strip()
            if item:
                result.append(item)
            buf = []
        else:
            buf.append(ch)

    last = "".join(buf).strip()
    if last:
        result.append(last)

    return [item for item in result if item]

def extract_number(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"(\d+(?:\.\d+)?)", str(text))
    return match.group(1) if match else ""

def extract_true_false(text: str) -> bool:
    return str(text).strip().upper() in ("YES", "Y")

def _parse_spec_raw(raw: str, parse: str | None) -> str:
    if parse == "number":
        return extract_number(raw)
    if parse == "strip":
        return raw.strip()
    return raw

def split_and_filter_patterns(
    value: str,
    exclude_patterns: list[str] | None = None,
) -> list[str]:
    """
    "GDDR6 SDRAM, LPDDR5X SDRAM"
    -> ["LPDDR5X SDRAM"]

    exclude_patterns:
        ["GDDR* SDRAM"]
    """
    if not value:
        return []

    exclude_patterns = exclude_patterns or []

    items = [
        x.strip()
        for x in str(value).split(",")
        if x.strip()
    ]

    result = []

    for item in items:
        if any(
            fnmatch.fnmatch(item.upper(), pattern.upper())
            for pattern in exclude_patterns
        ):
            continue

        result.append(item)

    return result

def resolve_spec_field(
    specs: dict | None,
    paths: list[tuple[str, str]],
    *,
    parse: str | None = "number",
    prefer_keywords: list[str] | None = None,
) -> str:
    """
    Map one internal scalar from several retailer group/key paths on the same site.

    When multiple paths have values:
    - If prefer_keywords is set (e.g. \"thread\" for threads), pick the first path (in
      priority order) whose raw text contains a keyword.
    - Otherwise use path priority: first path with a non-empty parsed value wins.

    Nothing is written to product JSON — only the resolved string is returned.
    """
    candidates: list[tuple[int, str, str]] = []
    for order, (group, key) in enumerate(paths):
        raw = spec_value(specs, group, key)
        if not raw:
            continue
        parsed = _parse_spec_raw(raw, parse)
        if parse == "number" and not parsed:
            continue
        if parse == "strip" and not parsed:
            continue
        candidates.append((order, raw, parsed))

    if not candidates:
        return ""

    if prefer_keywords:
        keywords = [k.lower() for k in prefer_keywords if k]
        for order, raw, parsed in sorted(candidates, key=lambda c: c[0]):
            raw_l = raw.lower()
            if any(kw in raw_l for kw in keywords):
                return parsed

    return sorted(candidates, key=lambda c: c[0])[0][2]


def resolve_spec_paths(
    specs: dict | None,
    paths: list[tuple[str, str]],
    *,
    parse: str | None = "number",
) -> tuple[str, str, str]:
    """Backward-compatible helper; prefer resolve_spec_field for normalizers."""
    value = resolve_spec_field(specs, paths, parse=parse)
    if not value:
        return "", "", ""
    for group, key in paths:
        raw = spec_value(specs, group, key)
        if not raw:
            continue
        if parse == "number" and extract_number(raw) == value:
            return value, raw, f"{group} > {key}"
        if parse != "number" and _parse_spec_raw(raw, parse) == value:
            return value, raw, f"{group} > {key}"
    return value, "", ""

if __name__ == "__main__":
    pass