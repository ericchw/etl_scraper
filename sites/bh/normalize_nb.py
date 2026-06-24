"""B&H → internal partial for notebooks (NB): packaging + content."""

from __future__ import annotations

from core.schema.registry import empty_internal
from sites.bh.content import parse_description_from_raw, parse_features_from_raw
from sites.bh.normalize_shared import fill_bh_packaging
import json

def normalize_bh_nb(raw: dict) -> dict:
    print(">>> normalize_bh_mnt loaded <<<")
    internal = empty_internal("NB")
    specs = raw.get("specs") or {}
    dim_unit = raw.get("dim_unit", "in")
    weight_unit = raw.get("weight_unit", "lb")

    fill_bh_packaging(internal, specs, dim_unit=dim_unit, weight_unit=weight_unit)

    internal["identity"]["mpn"] = str(raw.get("mpn") or "").strip().upper()
    internal["content"]["features"] = parse_features_from_raw(raw)
    desc = parse_description_from_raw(raw)
    if desc:
        internal["content"]["description"] = desc

    print("normalize_bh_mnt")
    print("BH FINAL", internal["physical"])
    return internal
