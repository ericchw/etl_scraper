"""Arctic → internal for HDD / SSD cooling products (sub_code HDD-SSD-COOL)."""

from __future__ import annotations

import re

from core.schema.registry import empty_internal
from core.spec_lookup import spec_list, spec_value
from core.units import length_to_in, weight_to_lb
from sites.cdw._common import fill_identity_content
from sites.manufacturers.arctic.normalize_cpu_aio import (
    _labelled_dimensions_to_in,
    _packaging_dims,
    warranty_to_days,
)


def _spec_any(specs: dict, key: str, *, match_suffix: bool = False) -> str:
    """Find a spec value in any scraped group (collapse titles vary by page)."""
    if not isinstance(specs, dict):
        return ""
    target = key.strip().lower()
    for block in specs.values():
        if not isinstance(block, dict):
            continue
        for k, v in block.items():
            source = re.sub(r"\s+#\d+$", "", str(k).strip()).lower()
            if source == target or (match_suffix and source.endswith(f" {target}")):
                text = "" if v is None else str(v).strip()
                if text and text.lower() != "none":
                    return text
    return ""


def _spec_lookup(specs: dict, group: str, key: str, **kwargs) -> str:
    """Compatible with fill_identity_content (group, key) and cross-group Arctic specs."""
    val = spec_value(specs, group, key, **kwargs)
    if val:
        return val
    return _spec_any(specs, key, match_suffix=bool(kwargs.get("match_suffix")))


def _spec_list_any(specs: dict, key: str) -> list[str]:
    value = _spec_any(specs, key)
    if not value:
        return []
    parts = re.split(r"[;,|\r\n]+", value)
    return [p.strip() for p in parts if p.strip()]


def _parse_dimensions(specs: dict) -> dict[str, str]:
    raw = (
        _spec_any(specs, "Dimensions")
        or _spec_any(specs, "Dimension")
        or ""
    )
    if raw:
        return _labelled_dimensions_to_in(raw)
    length = _spec_any(specs, "Length")
    width = _spec_any(specs, "Width")
    height = _spec_any(specs, "Height")
    return {
        k: v
        for k, v in (
            ("length_in", length_to_in(length) if length else ""),
            ("width_in", length_to_in(width) if width else ""),
            ("height_in", length_to_in(height) if height else ""),
        )
        if v
    }


def _included_items(specs: dict) -> list[str]:
    items: list[str] = []
    for block in specs.values():
        if not isinstance(block, dict):
            continue
        for key, val in block.items():
            if not isinstance(key, str):
                continue
            lower = key.lower()
            if lower.startswith("included") or "thermal pad" in lower or lower.startswith("accessories"):
                text = str(val).strip()
                if text and text not in items:
                    items.append(text)
    for entry in _spec_list_any(specs, "Included"):
        if entry and entry not in items:
            items.append(entry)
    return items


def _packaging_dims_any(specs: dict) -> dict[str, str]:
    """Packaging dims may live in the same group as item specs on Arctic pages."""
    widths: list[str] = []
    heights: list[str] = []
    lengths: list[str] = []
    weights: list[str] = []
    for block in specs.values():
        if not isinstance(block, dict):
            continue
        for key, val in block.items():
            base = re.sub(r"\s+#\d+$", "", str(key).strip()).lower()
            text = str(val).strip()
            if not text:
                continue
            if base == "width":
                widths.append(text)
            elif base == "height":
                heights.append(text)
            elif base == "length" and " x " not in text.lower():
                lengths.append(text)
            elif base == "weight":
                weights.append(text)
    out: dict[str, str] = {}
    if lengths:
        out["length_in"] = length_to_in(lengths[-1])
    if widths:
        out["width_in"] = length_to_in(widths[-1])
    if heights:
        out["height_in"] = length_to_in(heights[-1])
    if len(weights) >= 2:
        out["package_lb"] = weight_to_lb(weights[-1])
    elif len(weights) == 1 and "kg" in weights[0].lower():
        out["package_lb"] = weight_to_lb(weights[0])
    return out


def _drive_form_factors(title: str, features: list[str], specs: dict) -> list[str]:
    haystack = " ".join([title, *features]).upper()
    found: list[str] = []
    patterns = (
        ("2280", "M.2 2280"),
        ("22110", "M.2 22110"),
        ("2242", "M.2 2242"),
        ("2260", "M.2 2260"),
        ("M.2", "M.2"),
        ('2.5"', '2.5"'),
        ('3.5"', '3.5"'),
    )
    for token, label in patterns:
        if token in haystack and label not in found:
            found.append(label)
    for entry in _spec_list_any(specs, "Compatibility") + _spec_list_any(specs, "Drive Form Factor"):
        if entry not in found:
            found.append(entry)
    return found


def _ps5_compatible(title: str, description: str, features: list[str]) -> bool:
    haystack = " ".join([title, description, *features]).lower()
    return "ps5" in haystack or "playstation 5" in haystack


def _single_double_sided(title: str, description: str, features: list[str]) -> str:
    haystack = " ".join([title, description, *features]).lower()
    if "single-sided" in haystack and "double-sided" in haystack:
        return "single and double sided"
    if "double-sided" in haystack:
        return "double sided"
    if "single-sided" in haystack:
        return "single sided"
    return ""


def normalize_arctic_hdd_ssd_cool(
    raw: dict,
    *,
    product_code: str = "HDD-SSD-COOL",
    sub_code: str = "HDD-SSD-COOL",
) -> dict:
    specs = raw.get("specs") or {}
    title = str(raw.get("title") or "").strip()
    description = str(raw.get("description") or "").strip()
    features = [str(f).strip() for f in (raw.get("features") or []) if str(f).strip()]

    internal = empty_internal(product_code)

    fill_identity_content(
        internal,
        raw=raw,
        cdw=raw,
        specs=specs,
        spec_value=_spec_lookup,
    )
    internal["identity"]["brand"] = internal["identity"].get("brand") or "Arctic"
    internal["identity"]["product_type"] = (
        _spec_any(specs, "Product Type") or "HDD SSD Cooler"
    )
    internal["identity"]["model"] = str(raw.get("mpn") or internal["identity"].get("model") or "")

    internal["storage_cooling"]["product_type"] = internal["identity"]["product_type"]
    internal["storage_cooling"]["drive_form_factor"] = _drive_form_factors(title, features, specs)
    internal["storage_cooling"]["drive_interface"] = (
        _spec_list_any(specs, "Interface") or _spec_list_any(specs, "Drive Interface")
    )
    internal["storage_cooling"]["ps5_compatible"] = _ps5_compatible(title, description, features)
    internal["storage_cooling"]["single_double_sided"] = _single_double_sided(
        title, description, features
    )
    internal["storage_cooling"]["material"] = _spec_any(specs, "Material")
    internal["storage_cooling"]["assembly_type"] = _spec_any(specs, "Assembly")
    internal["storage_cooling"]["thermal_pads_included"] = [
        item
        for item in _included_items(specs)
        if "tp-" in item.lower() or "thermal pad" in item.lower() or "pad" in item.lower()
    ]

    internal["included_items"] = _included_items(specs) or internal["storage_cooling"]["thermal_pads_included"]

    item_dims = _parse_dimensions(specs)
    internal["physical"]["dimensions"]["item"].update(item_dims)
    item_weight = _spec_any(specs, "Weight")
    if item_weight:
        internal["physical"]["weight"]["item_lb"] = weight_to_lb(item_weight)

    dims = _packaging_dims(specs) or _packaging_dims_any(specs)
    internal["physical"]["dimensions"]["package"].update(
        {k: v for k, v in dims.items() if k.endswith("_in") and v}
    )
    if dims.get("package_lb"):
        internal["physical"]["weight"]["package_lb"] = dims["package_lb"]

    internal["warranty"] = warranty_to_days(_spec_any(specs, "Warranty"))

    upc = _spec_any(specs, "UPC")
    if upc:
        internal["identity"]["upc"] = upc

    internal.setdefault("_meta", {})["sub_code"] = sub_code
    return internal
