"""Load scrape merge source order from config."""

from __future__ import annotations

import json
from pathlib import Path
from core.conditions import resolve_condition

ROOT = Path(__file__).resolve().parent.parent
MERGE_SOURCES_PATH = ROOT / "configs" / "merge_sources.json"


def _stored_raw(
    source: str,
    mpn_key: str,
    raw_by_source: dict[str, dict],
) -> dict | None:
    """Raw scrape for a source: in-memory batch or products/{MPN}.json scraped_data."""
    raw = raw_by_source.get(source)
    if raw:
        return raw
    from core.cache import load_product_scraped_source

    return load_product_scraped_source(mpn_key, source)


MANUFACTURERS_PATH = ROOT / "configs" / "manufacturers.json"

DEFAULT_MERGE = {
    "spec": ["cdw", "bh", "manufacturer"],
    "packing": ["bh", "cdw", "manufacturer"],
    "photo": ["cdw", "bh", "manufacturer"],
    "features": ["bh", "cdw", "manufacturer"],
    "design": ["bh", "cdw", "manufacturer"],
}


def load_merge_sources() -> dict:
    if not MERGE_SOURCES_PATH.exists():
        return dict(DEFAULT_MERGE)
    with open(MERGE_SOURCES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return dict(DEFAULT_MERGE)
    return {
        "spec": list(data.get("spec") or DEFAULT_MERGE["spec"]),
        "packing": list(data.get("packing") or DEFAULT_MERGE["packing"]),
        "photo": list(data.get("photo") or DEFAULT_MERGE["photo"]),
        "features": list(data.get("features") or DEFAULT_MERGE["features"]),
        "design": list(data.get("design") or DEFAULT_MERGE["design"]),
    }


def save_merge_sources(
    spec: list[str],
    packing: list[str],
    photo: list[str] | None = None,
    features: list[str] | None = None,
    design: list[str] | None = None,
) -> None:
    cfg = load_merge_sources()
    MERGE_SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "spec": spec,
        "packing": packing,
        "photo": photo if photo is not None else cfg.get("photo", DEFAULT_MERGE["photo"]),
        "features": features if features is not None else cfg.get("features", DEFAULT_MERGE["features"]),
        "design": design if design is not None else cfg.get("design", DEFAULT_MERGE["design"]),
    }
    with open(MERGE_SOURCES_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def scrape_visit_order() -> tuple[str, ...]:
    """
    Browser visit order: spec priorities first, then packing-only sources, then photo-only.

    Example config spec [cdw,bh,mfg] + packing [bh,cdw,mfg] -> cdw, bh, manufacturer.
  """
    cfg = load_merge_sources()
    ordered: list[str] = []
    for name in cfg["spec"] + cfg["packing"] + cfg["features"] + cfg["design"] + cfg["photo"]:
        if name not in ordered:
            ordered.append(name)
    return tuple(ordered)


def configured_scrape_sources() -> tuple[str, ...]:
    """Unique sources that may be scraped (same order as scrape_visit_order)."""
    return scrape_visit_order()


def _raw_has_spec_content(raw: dict | None) -> bool:
    if not raw:
        return False
    specs = raw.get("specs")
    if isinstance(specs, dict) and specs:
        return True
    return bool(str(raw.get("title") or "").strip())


def _raw_has_packaging(raw: dict | None) -> bool:
    if not raw:
        return False
    specs = raw.get("specs") or {}
    if not isinstance(specs, dict):
        return False
    for group in ("Package Dimensions", "Packaging Info"):
        block = specs.get(group)
        if not isinstance(block, dict):
            continue
        for key, val in block.items():
            if val and str(val).strip():
                kl = key.lower()
                if "weight" in kl or "dimension" in kl or "length" in kl:
                    return True
    return False


def should_scrape_source(
    source: str,
    *,
    mpn_key: str,
    rescrape: bool,
    raw_by_source: dict[str, dict],
    submission: dict | None,
) -> tuple[bool, str]:
    """
    Whether to open the browser for this source.

    Returns (scrape, reason).
    """
    if not rescrape:
        raw = _stored_raw(source, mpn_key, raw_by_source)
        if raw:
            if source == "bh" and _raw_has_packaging(raw):
                return False, "product has B&H packaging"
            if source != "manufacturer" and _raw_has_spec_content(raw):
                return False, "product has scraped_data"
            if source == "manufacturer":
                return False, "product has manufacturer scrape"

    cfg = load_merge_sources()
    spec_order = [s for s in cfg["spec"] if s != "manufacturer"]

    if source == "cdw":
        return True, "spec primary"

    if source == "bh":
        cdw_raw = raw_by_source.get("cdw")
        if not _raw_has_spec_content(cdw_raw):
            return True, "CDW missing spec — B&H fallback"
        if not _raw_has_packaging(raw_by_source.get("bh")):
            return True, "packing (B&H priority)"
        return True, "packing (B&H priority)"

    if source == "manufacturer":
        brand = (submission or {}).get("manufacturer", "").strip()
        mcfg = manufacturer_config(brand)
        if not mcfg:
            return False, f"no manufacturer config for {brand!r}"
        if mcfg.get("enabled") is False:
            return False, f"{brand} disabled in manufacturers.json"
        for prior in spec_order:
            if prior == "manufacturer":
                continue
            if _raw_has_spec_content(raw_by_source.get(prior)):
                return False, f"{prior} already has spec"
        return True, "spec fallback (CDW/B&H insufficient)"

    return True, "configured source"


def format_merge_priority_log() -> str:
    cfg = load_merge_sources()
    return (
        f"spec: {' > '.join(cfg['spec'])} | "
        f"packing: {' > '.join(cfg['packing'])} | "
        f"features: {' > '.join(cfg['features'])} | "
        f"design: {' > '.join(cfg['design'])} | "
        f"photo: {' > '.join(cfg['photo'])}"
    )


def load_manufacturers() -> dict:
    if not MANUFACTURERS_PATH.exists():
        return {}
    with open(MANUFACTURERS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def manufacturer_config(brand: str) -> dict | None:
    key = (brand or "").strip().lower().replace(" ", "_")
    if not key:
        return None
    cfg = load_manufacturers().get(key)
    return cfg if isinstance(cfg, dict) else None


