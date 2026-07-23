"""Internal product paths and envelope (schemas live in registry + configs/schemas/)."""

from __future__ import annotations

import copy
from typing import Any

from core.schema.registry import DEFAULT_PRODUCT_CODE, empty_internal as _empty_internal
from sites.cdw.normalizer import normalize_cdw_raw

def empty_internal(product_code: str = DEFAULT_PRODUCT_CODE) -> dict[str, Any]:
    return _empty_internal(product_code)


def get_path(data: dict | None, path: str) -> Any:
    if not data or not path:
        return None
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def set_path(data: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        nxt = current.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            current[part] = nxt
        current = nxt
    current[parts[-1]] = value


def envelope_from_internal(
    internal: dict[str, Any],
    *,
    product_code: str = DEFAULT_PRODUCT_CODE,
    sub_code: str = "",
) -> dict[str, Any]:
    identity = internal.get("identity") or {}
    code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()
    envelope: dict[str, Any] = {
        "mpn": identity.get("mpn") or "",
        "product_code": code,
        "internal": internal,
    }
    sub = (sub_code or (internal.get("_meta") or {}).get("sub_code") or "").strip().upper()
    if sub:
        envelope["sub_code"] = sub
    return envelope


def ensure_internal(product: dict) -> dict[str, Any]:
    """Return internal block, rebuilding from scraped_data when missing."""
    if isinstance(product.get("internal"), dict) and product["internal"]:
        return product["internal"]


    code = (product.get("product_code") or DEFAULT_PRODUCT_CODE).strip().upper()
    raw = {
        "source": product.get("source", "cdw"),
        "title": product.get("title"),
        "mpn": product.get("mpn"),
        "description": product.get("description"),
        "features": product.get("features"),
        "images": product.get("images") or product.get("scraped_image_urls"),
        "scraped_data": product.get("scraped_data") or {},
    }
    return normalize_cdw_raw(raw, product_code=code)

def deep_merge_dict(base: dict, overlay: dict) -> dict:
    out = copy.deepcopy(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge_dict(out[key], val)
        elif val not in (None, [], {}):
            out[key] = copy.deepcopy(val)
    return out
