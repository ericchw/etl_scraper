"""B&H → internal partial for monitors (MNT): display + packaging + content."""

from __future__ import annotations

from core.schema.registry import empty_internal
from core.spec_lookup import extract_number, spec_value, spec_list
from sites.bh.content import parse_description_from_raw, parse_features_from_raw
from sites.bh.normalize_shared import fill_bh_packaging

import json

def normalize_bh_mnt(raw: dict) -> dict:
    internal = empty_internal("MNT")
    specs = raw.get("specs") or {}
    dim_unit = raw.get("dim_unit", "in")
    weight_unit = raw.get("weight_unit", "lb")

    fill_bh_packaging(internal, specs, dim_unit=dim_unit, weight_unit=weight_unit)

    internal["identity"]["mpn"] = str(raw.get("mpn") or "").strip().upper()
    internal["content"]["features"] = parse_features_from_raw(raw)
    # desc = parse_description_from_raw(raw)
    # if desc:
    #     internal["content"]["description"] = desc
    #
    # disp = internal["display"]
    # disp["size_in"] = extract_number(
    #     spec_value(specs, "DISPLAY", "Size")
    #     or spec_value(specs, "Display", "Screen Size")
    # )
    # disp["resolution"] = spec_value(specs, "DISPLAY", "Resolution") or spec_value(
    #     specs, "DISPLAY", "Native Resolution"
    # )
    # disp["refresh_rate_hz"] = extract_number(
    #     spec_value(specs, "DISPLAY", "Refresh Rate")
    # )
    # disp["panel_type"] = spec_value(specs, "DISPLAY", "Panel Type")
    # disp["display_type"] = disp["panel_type"]
    # disp["aspect_ratio"] = spec_value(specs, "DISPLAY", "Aspect Ratio")
    #
    # internal["io"]["interfaces"] = spec_list(specs, "CONNECTIVITY", "USB I/O")

    return internal
