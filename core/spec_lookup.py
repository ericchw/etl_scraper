"""Read nested retailer spec dicts (fuzzy group/key) and resolve multi-path candidates."""

from __future__ import annotations
import fnmatch
import re
from typing import Any

def spec_value(
    specs: dict | None,
    path: list[str] | tuple[str, ...] | str,
    key: str | None = None,
    *,
    match_suffix: bool = False,
    last: bool = False,
) -> str:
    """
    Case-insensitive nested spec lookup.

    New style:
        spec_value(
            specs,
            [
                "General Specifications",
                "Pump/Tubing Specifications",
                "Min rpm"
            ]
        )

    Old style still supported:
        spec_value(
            specs,
            "General Specifications",
            "Min rpm"
        )
    """

    if not isinstance(specs, dict):
        return ""

    # Backward compatibility:
    # spec_value(specs, group, key)
    if isinstance(path, str) and key is not None:
        path = [path, key]

    # Single string lookup
    elif isinstance(path, str):
        path = [path]

    current = specs

    # Walk nested layers except final key
    for layer in path[:-1]:

        if not isinstance(current, dict):
            return ""

        target = layer.strip().lower()

        found = None

        for k, v in current.items():
            if str(k).strip().lower() == target:
                found = v
                break

        if found is None:
            return ""

        current = found

    if not isinstance(current, dict):
        return ""

    # Final key lookup
    target_key = str(path[-1]).strip().lower()

    matches = []

    for k, v in current.items():

        source_key = re.sub(
            r"\s+#\d+$",
            "",
            str(k).strip()
        ).lower()

        if (
            source_key == target_key
            or (
                match_suffix
                and source_key.endswith(f" {target_key}")
            )
        ):
            value = "" if v is None else str(v).strip()

            if value and value.lower() != "none":
                matches.append(value)

    if not matches:
        return ""

    return matches[-1] if last else matches[0]

# def spec_value(
#     specs: dict | None,
#     group: str,
#     key: str,
#     *,
#     match_suffix: bool = False,
#     last: bool = False,
# ) -> str:
#     """Case-insensitive spec lookup, optionally matching section-prefixed keys."""
#     if not isinstance(specs, dict):
#         return ""
#
#     target_group = group.strip().lower()
#     matched_block: dict = {}
#     for g_key, g_val in specs.items():
#         if str(g_key).strip().lower() == target_group and isinstance(g_val, dict):
#             matched_block = g_val
#             break
#
#     if not matched_block:
#         return ""
#
#     target_key = key.strip().lower()
#     matches: list[str] = []
#     for k, v in matched_block.items():
#         source_key = re.sub(r"\s+#\d+$", "", str(k).strip()).lower()
#         if source_key == target_key or (match_suffix and source_key.endswith(f" {target_key}")):
#             value = "" if v is None else str(v).strip()
#             if value and value.lower() != "none":
#                 matches.append(value)
#
#     if not matches:
#         return ""
#     return matches[-1] if last else matches[0]

# def spec_list(
#     specs: dict | None,
#     group: str,
#     key: str,
#     *,
#     separators: str = r"[,;/|\r\n]"
# ) -> list[str]:
#     value = spec_value(specs, group, key)
#
#     if not value:
#         return []
#
#     pattern = re.compile(separators)
#
#     result = []
#     buf = []
#     depth = 0
#
#     for ch in value:
#         if ch == "(":
#             depth += 1
#         elif ch == ")":
#             depth = max(0, depth - 1)
#
#         if depth == 0 and pattern.match(ch):
#             item = "".join(buf).strip()
#             if item:
#                 result.append(item)
#             buf = []
#         else:
#             buf.append(ch)
#
#     last = "".join(buf).strip()
#     if last:
#         result.append(last)
#
#     return [item for item in result if item]

def spec_list(
    specs: dict | None,
    path: list[str] | tuple[str, ...] | str,
    key: str | None = None,
    *,
    separators: str = r"[,;/|\r\n]",
    match_suffix: bool = False,
    last: bool = False,
) -> list[str]:
    """
    Get a spec value and split into a list.

    New style:
        spec_list(
            specs,
            [
                "General Specifications",
                "Pump/Tubing Specifications",
                "Tube Outer Diameter"
            ]
        )

    Old style:
        spec_list(
            specs,
            "General Specifications",
            "Tube Outer Diameter"
        )
    """

    value = spec_value(
        specs,
        path,
        key,
        match_suffix=match_suffix,
        last=last
    )

    if not value:
        return []

    # Support literal multi-character separators
    if len(separators) > 1 and not separators.startswith("["):
        splitters = [separators]
    else:
        splitters = None

    result = []
    buf = []
    depth = 0
    i = 0

    pattern = re.compile(separators) if not splitters else None

    while i < len(value):

        ch = value[i]

        if ch == "(":
            depth += 1

        elif ch == ")":
            depth = max(0, depth - 1)

        matched = False

        if depth == 0:

            if splitters:

                for sep in splitters:

                    if value.startswith(sep, i):

                        item = "".join(buf).strip()

                        if item:
                            result.append(item)

                        buf = []
                        i += len(sep)
                        matched = True
                        break

            elif pattern and pattern.match(ch):

                item = "".join(buf).strip()

                if item:
                    result.append(item)

                buf = []
                matched = True
                i += 1

        if not matched:
            buf.append(ch)
            i += 1

    last_item = "".join(buf).strip()

    if last_item:
        result.append(last_item)

    return [
        item
        for item in result
        if item
    ]

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

def match_any(text: str, target_str_list: list[str]) -> bool:
    text = text.strip().lower()
    if "*" in target_str_list:
        return bool(text)
    print(text, any(t.lower() in text for t in target_str_list))
    return any(t.lower() in text for t in target_str_list)

def to_int_number(text: str) -> int | None:
    text = text.strip().lower()

    scale_map = {
        "hundred": 100,
        "thousand": 1_000,
        "million": 1_000_000,
        "billion": 1_000_000_000,
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000,
    }

    # extract number + scale anywhere in the string (ignore trailing words like "colors")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(hundred|thousand|million|billion|k|m|b)?", text)
    if not match:
        return None

    num = float(match.group(1))
    scale = match.group(2)

    if scale:
        num *= scale_map[scale]

    return int(num)

if __name__ == "__main__":
    text = "Height, Pivot (rotation), Swivel, Tilt"
    targets = ["pivot", "swivel"]
    print(match_any(text, targets))

    print(to_int_number("1.07 Billion Colors (10-Bit)"))

    pass
