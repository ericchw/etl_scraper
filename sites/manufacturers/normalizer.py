"""Manufacturer raw scrape → partial internal (brand + sub_code dispatch)."""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path

from core.schema.registry import DEFAULT_PRODUCT_CODE, empty_internal

ROOT = Path(__file__).resolve().parent.parent.parent
MFG_NORM_CATEGORIES_PATH = ROOT / "configs" / "manufacturers" / "normalize_categories.json"


@lru_cache(maxsize=1)
def load_manufacturer_normalize_categories() -> dict:
    if not MFG_NORM_CATEGORIES_PATH.exists():
        return {}
    with open(MFG_NORM_CATEGORIES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _brand_key(raw: dict) -> str:
    return str(raw.get("brand") or "").strip().lower().replace(" ", "_")


def _resolve_normalizer_fn(brand: str, normalizer_key: str):
    """Import sites.manufacturers.{brand}.{module} from normalize_categories.json."""
    entry = load_manufacturer_normalize_categories().get(normalizer_key) or {}
    brands = entry.get("brands") if isinstance(entry.get("brands"), dict) else {}
    module_name = brands.get(brand) or brands.get("default")

    if module_name:
        try:
            module = importlib.import_module(f"sites.manufacturers.{brand}.{module_name}")
            for fn_name in (
                f"normalize_{brand}_raw",
                f"normalize_{brand}_{module_name.removeprefix('normalize_')}",
                module_name,
            ):
                fn = getattr(module, fn_name, None)
                if callable(fn):
                    return fn
        except ModuleNotFoundError:
            pass

    try:
        pkg = importlib.import_module(f"sites.manufacturers.{brand}.normalizer")
        fn = getattr(pkg, f"normalize_{brand}_raw", None)
        if callable(fn):
            return fn
    except ModuleNotFoundError:
        pass
    return None


def schema_code_for_normalizer_key(normalizer_key: str, *, product_code: str) -> str:
    entry = load_manufacturer_normalize_categories().get(normalizer_key) or {}
    schema = str(entry.get("schema") or entry.get("code") or product_code or "").strip().upper()
    return schema or product_code


def normalize_manufacturer_raw(
    raw: dict,
    *,
    product_code: str = DEFAULT_PRODUCT_CODE,
    normalizer_key: str | None = None,
) -> dict:
    code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()
    norm_key = (normalizer_key or code).strip().upper()
    schema_code = schema_code_for_normalizer_key(norm_key, product_code=code)

    brand = _brand_key(raw)
    fn = _resolve_normalizer_fn(brand, norm_key) if brand else None
    if fn:
        return fn(raw, product_code=schema_code, sub_code=norm_key)

    internal = empty_internal(schema_code)
    internal["identity"]["brand"] = str(raw.get("brand") or "").strip()
    internal["identity"]["mpn"] = str(raw.get("mpn") or "").strip().upper()
    internal["content"]["title"] = str(raw.get("title") or "").strip()
    internal["content"]["description"] = str(raw.get("description") or "").strip()
    internal["content"]["features"] = list(raw.get("features") or [])
    internal["content"]["images"] = list(raw.get("images") or [])
    return internal
