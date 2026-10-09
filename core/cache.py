"""Product paths and optional legacy cache/ helpers (scrape uses products/ only)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Callable

from core.paths import safe_path_component

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
PRODUCTS_DIR = ROOT / "products"


def cache_raw_path(source: str, mpn: str) -> Path:
    key = safe_path_component((mpn or "").upper())
    return CACHE_DIR / safe_path_component(source) / f"{key}.json"


def cache_meta_path(source: str, mpn: str) -> Path:
    key = safe_path_component((mpn or "").upper())
    return CACHE_DIR / safe_path_component(source) / f"{key}.meta.json"


def product_path(mpn: str) -> Path:
    key = safe_path_component((mpn or "").upper())
    return PRODUCTS_DIR / f"{key}.json"


def legacy_json_path(mpn: str) -> Path:
    """Previous output/json/{mpn}.json location."""
    key = safe_path_component((mpn or "").upper())
    return ROOT / "output" / "json" / f"{key}.json"


def save_raw(
    source: str,
    mpn: str,
    data: dict,
    *,
    url: str = "",
    log: Callable[[str], None] = print,
) -> Path:
    path = cache_raw_path(source, mpn)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    meta = {
        "last_scraped": date.today().isoformat(),
        "source": source,
        "mpn": (mpn or "").strip().upper(),
        "url": url,
    }
    meta_path = cache_meta_path(source, mpn)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    log(f"CACHE {source} → {path}")
    return path


def load_raw(source: str, mpn: str) -> dict | None:
    path = cache_raw_path(source, mpn)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def has_raw(source: str, mpn: str) -> bool:
    return cache_raw_path(source, mpn).exists()


def load_product_scraped_data(mpn: str) -> dict[str, dict]:
    """Per-source raw blobs from products/{MPN}.json (canonical store)."""
    path = resolve_product_json_path(mpn)
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    scraped = data.get("scraped_data")
    if not isinstance(scraped, dict):
        return {}
    return {k: v for k, v in scraped.items() if isinstance(v, dict) and v}


def load_product_scraped_source(mpn: str, source: str) -> dict | None:
    return load_product_scraped_data(mpn).get(source)


def resolve_product_json_path(mpn: str) -> Path | None:
    """Prefer products/{mpn}.json, fall back to legacy output/json."""
    p = product_path(mpn)
    if p.exists():
        return p
    leg = legacy_json_path(mpn)
    if leg.exists():
        return leg
    return None
