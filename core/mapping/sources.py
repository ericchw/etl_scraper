"""Unified YAML `sources` resolution for the mapping engine."""

from __future__ import annotations

from typing import Any

from core.schema.product import get_path

_SOURCE_KEYS = frozenset({"source", "sources", "sources_first", "sources_join"})


def has_source_rule(rule: dict) -> bool:
    return any(key in rule for key in _SOURCE_KEYS)


def is_empty(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, (list, dict)) and len(val) == 0:
        return True
    if val == 0 or val == 0.0:
        return True
    return False


def source_entries(rule: dict) -> list[Any]:
    if "sources" in rule:
        entries = rule["sources"]
        return entries if isinstance(entries, list) else [entries]
    if "source" in rule:
        return [rule["source"]]
    if "sources_first" in rule:
        return list(rule["sources_first"])
    if "sources_join" in rule:
        return list(rule["sources_join"])
    return []


def _walk_dict_path(data: Any, keys: list) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _resolve_internal_path(context: dict, path: str | list) -> Any:
    if isinstance(path, str):
        return get_path(context["internal"], path)
    if isinstance(path, list):
        if path and path[0] == "internal":
            return _walk_dict_path(context, path)
        return _walk_dict_path(context["internal"], path)
    return None


def _text_passes_filters(text: str, rule: dict) -> bool:
    low = text.lower()
    include = rule.get("filter_include_keywords") or []
    if include and not any(keyword.lower() in low for keyword in include):
        return False
    exclude = rule.get("filter_exclude_keywords") or []
    if exclude and any(keyword.lower() in low for keyword in exclude):
        return False
    return True


def _list_join_sep(rule: dict, src: Any) -> str:
    if isinstance(src, dict) and src.get("join"):
        sep = src["join"]
    else:
        sep = rule.get("list_join") or rule.get("join") or ", "
    if isinstance(sep, list):
        return sep[0] if sep else ", "
    return str(sep)


def _format_list_value(val: list, rule: dict, src: Any) -> str | None:
    sep = _list_join_sep(rule, src)
    parts: list[str] = []
    for item in val:
        if is_empty(item):
            continue
        text = str(item).strip()
        if not text or not _text_passes_filters(text, rule):
            continue
        parts.append(text)
    if not parts:
        return None
    return sep.join(parts)


def _stringify_value(val: Any, rule: dict, src: Any) -> str | None:
    if is_empty(val):
        return None
    if isinstance(val, list):
        return _format_list_value(val, rule, src)
    text = str(val).strip()
    if not text or not _text_passes_filters(text, rule):
        return None
    return text


def _source_affixes(src: Any) -> tuple[str | None, str | None]:
    if not isinstance(src, dict):
        return None, None
    return src.get("prefix"), src.get("suffix")


def _apply_affixes(text: str, prefix: str | None, suffix: str | None) -> str:
    if prefix:
        text = f"{prefix}{text}"
    if suffix:
        text = f"{text}{suffix}"
    return text


def _resolve_mode(rule: dict) -> str:
    mode = rule.get("mode")
    if mode:
        return str(mode).lower()
    return "join" if rule.get("join") is not None else "first"


def _resolve_single_source(src: Any, context: dict) -> Any:
    get_spec = context["get_spec"]

    if isinstance(src, list):
        if src and src[0] == "internal":
            return get_path(context["internal"], ".".join(src[1:]))
        if len(src) == 2:
            return get_spec(src[0], src[1])
        return None

    if isinstance(src, dict):
        if "path" in src:
            return _resolve_internal_path(context, src["path"])
        if "group" in src and "key" in src:
            return get_spec(src["group"], src["key"])
    return None


def resolve_sources(rule: dict, context: dict) -> Any:
    """Resolve field value from unified `sources` (or legacy `source` aliases)."""
    entries = source_entries(rule)
    if not entries:
        return None

    mode = _resolve_mode(rule)
    join_sep = rule.get("join")
    parts: list[str] = []

    for src in entries:
        raw = _resolve_single_source(src, context)
        text = _stringify_value(raw, rule, src)
        if text is None:
            continue

        src_prefix, src_suffix = _source_affixes(src)
        text = _apply_affixes(text, src_prefix, src_suffix)

        if mode == "first":
            text = _apply_affixes(text, rule.get("prefix"), rule.get("suffix"))
            return text

        parts.append(text)

    if not parts:
        return ""

    if mode == "first":
        return ""

    if len(parts) == 1:
        result = parts[0]
    else:
        sep = join_sep if join_sep is not None else " "
        if isinstance(sep, list):
            sep = sep[0] if sep else " "
        result = str(sep).join(parts)

    return _apply_affixes(result, rule.get("prefix"), rule.get("suffix"))
