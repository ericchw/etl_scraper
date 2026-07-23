"""Internal category taxonomy → marketplace codes and export paths."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES_PATH = ROOT / "configs" / "categories" / "categories.json"

NEWEGG_BATCH_PREFIX = "ComputerHardware_BatchItemCreation_"
DEFAULT_PRODUCT_CODE = "NB"


def load_categories() -> dict:
    if not CATEGORIES_PATH.exists():
        return {}
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def get_category_entry(category_key: str) -> dict:
    return load_categories().get(category_key, {})


def category_enabled(category_key: str) -> bool:
    entry = get_category_entry(category_key)
    if not entry:
        return False
    return entry.get("enable", True) is not False


def enabled_categories() -> dict:
    return {
        key: entry
        for key, entry in load_categories().items()
        if isinstance(entry, dict) and entry.get("enable", True) is not False
    }


def product_code(category_key: str) -> str:
    """Product family for internal schema + SKU prefix (NB, MNT, ACC, …)."""
    code = str(get_category_entry(category_key).get("code") or "").strip().upper()
    return code or DEFAULT_PRODUCT_CODE


def sub_code(category_key: str) -> str:
    """Optional finer normalizer key (e.g. CPU-AIO under ACC)."""
    entry = get_category_entry(category_key)
    sub = str(entry.get("sub_code") or "").strip().upper()
    return sub


def normalizer_key(category_key: str) -> str:
    """
    Key for source-specific normalizer dispatch.
    Uses sub_code when present, otherwise product code (NB, MNT, …).
    """
    return sub_code(category_key) or product_code(category_key)


def sku_prefix(category_key: str) -> str:
    return product_code(category_key) or "XX"


def marketplace_code(category_key: str, marketplace: str) -> str:
    entry = get_category_entry(category_key)
    value = entry.get(marketplace, "")

    if marketplace == "newegg" and value and not value.startswith(NEWEGG_BATCH_PREFIX):
        return f"{NEWEGG_BATCH_PREFIX}{value}"

    return str(value)


def newegg_suffix(category_key: str) -> str:
    return str(get_category_entry(category_key).get("newegg", ""))


def bestbuy_category_id(category_key: str) -> str:
    return str(get_category_entry(category_key).get("bestbuy", ""))


def mapping_path(category_key: str, marketplace: str) -> Path | None:
    """YAML/headers named after marketplace category id, e.g. CAT_1002.yaml."""
    if marketplace == "bestbuy":
        cat_id = bestbuy_category_id(category_key)
        if cat_id:
            return ROOT / "configs" / "marketplaces" / "bestbuy" / f"{cat_id}.yaml"
    if marketplace == "newegg":
        suffix = newegg_suffix(category_key)
        if suffix:
            safe = suffix.replace("/", "_")
            return ROOT / "configs" / "marketplaces" / "newegg" / f"{safe}.yaml"
    return None


def template_csv_path(category_key: str, marketplace: str) -> Path | None:
    from core.marketplace_templates import resolve_template_csv

    path = resolve_template_csv(category_key, marketplace)
    return path if path and path.exists() else None
