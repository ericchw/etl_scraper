"""Merge partial internal products — safe structured merge (FIXED camera drop bug)."""

from __future__ import annotations

import copy
from typing import Any

from core.merge_policy import load_merge_sources
from core.schema.product import empty_internal, get_path, set_path
from core.schema.registry import DEFAULT_PRODUCT_CODE
import json

# ----------------------------
# utils
# ----------------------------

def _is_empty(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        return not val.strip()
    if isinstance(val, (list, dict)):
        return len(val) == 0
    return False


def _copy(val: Any) -> Any:
    if isinstance(val, (dict, list)):
        return copy.deepcopy(val)
    return val


def _field_policies() -> dict[str, tuple[str, ...]]:
    cfg = load_merge_sources()
    spec = tuple(cfg.get("spec") or ("cdw", "bh", "manufacturer"))
    packing = tuple(cfg.get("packing") or ("bh", "cdw", "manufacturer"))
    print(f"_field_policies: {spec}; {packing}")


    policies: dict[str, tuple[str, ...]] = {}

    # for dim in ("length_in", "width_in", "height_in"):
    #     policies[f"dimensions.package.{dim}"] = packing
    #     policies[f"dimensions.item.{dim}"] = spec
    #
    # policies["weight.package_lb"] = packing
    # policies["weight.item_lb"] = spec
    for dim in ("length_in", "width_in", "height_in"):
        policies[f"physical.dimensions.package.{dim}"] = packing
        policies[f"physical.dimensions.item.{dim}"] = spec

    policies["physical.weight.package_lb"] = packing
    policies["physical.weight.item_lb"] = spec

    return policies


# ----------------------------
# helpers
# ----------------------------

def _pick_scalar(path: str, partials: dict[str, dict], policy: tuple[str, ...]):
    for source in policy:
        partial = partials.get(source)
        if not partial:
            continue
        val = get_path(partial, path)
        if not _is_empty(val):
            return val, source
    return "", None


def _winner_source(partials: dict[str, dict], order: tuple[str, ...], *, check):
    for source in order:
        if check(partials.get(source)):
            return source
    return None


def _partial_has_spec(partial: dict | None, *, product_code: str = DEFAULT_PRODUCT_CODE) -> bool:
    if not partial:
        return False
    code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()
    if code == "MNT":
        disp = partial.get("display") or {}
        return bool(
            get_path(partial, "display.size_in")
            or get_path(partial, "display.resolution")
            or (isinstance(disp, dict) and disp.get("panel_type"))
            or get_path(partial, "identity.brand")
        )
    proc = partial.get("processor") or {}
    if isinstance(proc, dict) and (
        proc.get("model") or proc.get("brand") or proc.get("cores") or proc.get("threads")
    ):
        return True
    return bool(get_path(partial, "memory.capacity_gb") or get_path(partial, "display.size_in"))


def _overlay_partial(merged: dict, partial: dict) -> None:
    """Copy only keys that exist in the merged schema template."""
    for key, val in partial.items():
        if key.startswith("_") or key not in merged:
            continue
        if isinstance(merged[key], dict) and isinstance(val, dict):
            _overlay_partial(merged[key], val)
        elif isinstance(val, list):
            merged[key] = _copy(val)
        else:
            merged[key] = val


# ----------------------------
# COPY SPEC BLOCK (FIXED)
# ----------------------------

def _apply_spec_block(merged: dict, partial: dict) -> None:
    """
    FIX:
    - now safely copy all structured dict blocks
    """

    # 🔥 FIX: include camera + future-proof
    _overlay_partial(merged, partial)

    # scalar overrides (dimensions + weight item only)
    for path in (
        "dimensions.item.length_in",
        "dimensions.item.width_in",
        "dimensions.item.height_in",
        "weight.item_lb",
    ):
        val = get_path(partial, path)
        if not _is_empty(val):
            set_path(merged, path, val)

    items = get_path(partial, "included_items")
    if isinstance(items, list) and items:
        merged["included_items"] = _copy(items)


# ----------------------------
# content helpers
# ----------------------------

def _pick_images(partials, photo_order):
    for source in photo_order:
        urls = get_path(partials.get(source, {}), "content.images") or []
        if isinstance(urls, list) and urls:
            cleaned = [u.strip() for u in urls if str(u).strip()]
            if cleaned:
                return cleaned, source
    return [], None


def _pick_features(partials, features_order):
    for source in features_order:
        feats = get_path(partials.get(source, {}), "content.features") or []
        if isinstance(feats, list) and feats:
            cleaned = [f.strip() for f in feats if str(f).strip()]
            if cleaned:
                return cleaned, source
    return [], None


def _pick_description(partials, design_order):
    for source in design_order:
        text = get_path(partials.get(source, {}), "content.description")
        if not _is_empty(text):
            return str(text), source
    return "", None


def _extract_packaging_specs(partials, packing_order):
    print("_extract_packaging_specs partial:", partials)
    print("_extract_packaging_specs packing_order:", packing_order)
    for source in packing_order:
        partial = partials.get(source) or {}

        pkg = partial.get("packaging_specs")
        if isinstance(pkg, dict) and pkg:
            return _copy(pkg), source

    return {}, None


# ----------------------------
# MAIN MERGE
# ----------------------------

def merge_internals(
    partials: dict[str, dict],
    *,
    product_code: str = DEFAULT_PRODUCT_CODE,
    source_order=None,
):
    cfg = load_merge_sources()

    spec_order = tuple(cfg.get("spec") or ("cdw", "bh", "manufacturer"))
    packing_order = tuple(cfg.get("packing") or ("bh", "cdw", "manufacturer"))
    photo_order = tuple(cfg.get("photo") or spec_order)
    features_order = tuple(cfg.get("features") or spec_order)
    design_order = tuple(cfg.get("design") or features_order)

    code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()
    merged = empty_internal(code)
    report = {"product_code": code}

    def _has_spec(partial: dict | None) -> bool:
        return _partial_has_spec(partial, product_code=code)

    # ---------------- spec winner ----------------
    spec_source = _winner_source(partials, spec_order, check=_has_spec)
    if spec_source:
        _apply_spec_block(merged, partials[spec_source])
        print("AFTER APPLY SPEC: ", merged["physical"])
        report["spec"] = spec_source
    else:
        report["spec"] = "none"

    # ---------------- scalar fields ----------------
    policies = _field_policies()
    for path, policy in policies.items():
        val, winner = _pick_scalar(path, partials, policy)
        print("path, val, winner: ", path, "-", val, "-", winner)
        if not _is_empty(val):
            set_path(merged, path, val)
            if winner:
                report[path] = winner
        if path.startswith("physical"):
            print('if path.startswith("physical"): path, val, winner: ', path, "-", val, "-", winner)

    # ---------------- content ----------------
    images, img_src = _pick_images(partials, photo_order)
    if images:
        merged.setdefault("content", {})["images"] = images
        report["content.images"] = img_src

    features, feat_src = _pick_features(partials, features_order)
    if features:
        merged.setdefault("content", {})["features"] = features
        report["content.features"] = feat_src

    desc, desc_src = _pick_description(partials, design_order)
    if desc:
        merged.setdefault("content", {})["description"] = desc
        report["content.description"] = desc_src

    pkg, pkg_src = _extract_packaging_specs(partials, packing_order)
    if pkg:
        merged["packaging_specs"] = pkg
        report["packaging_specs"] = pkg_src

    print("merge_internalsSPEC SOURCE=", spec_source)
    print("merge_internals pkg, pkg_src=", pkg, pkg_src)

    print("merge_internals partials=", partials)

    return merged, report