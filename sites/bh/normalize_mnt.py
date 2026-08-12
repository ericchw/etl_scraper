"""B&H → internal partial for monitors (MNT): display + packaging + content."""

from __future__ import annotations

from core.schema.registry import empty_internal
from core.spec_lookup import extract_number, spec_value, spec_list, match_any, to_int_number
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

    # display
    internal["display"]["size_in"] = extract_number(spec_value(specs, "Key Specs", "Display Size")) or extract_number(spec_value(specs, "Display", "Size"))
    internal["display"]["panel"] = spec_value(specs, "Key Specs", "Panel Type") or spec_value(specs, "Display", "Panel Type")
    internal["display"]["resolution"] = spec_value(specs, "Key Specs", "Native Resolution") or spec_value(specs, "Display", "Native Resolution")
    internal["display"]["hdr"]["hdr_capable"] = match_any(spec_value(specs, "Key Specs", "HDR Support"),["yes"])
    internal["display"]['hdr']["hdr_format"] = spec_value(specs, "Key Specs", "HDR Support").split(":", 1)[1].strip() if "yes" in spec_value(specs, "Key Specs", "HDR Support").lower() else spec_value(specs, "Key Specs","HDR Support")
    internal["display"]["color_support"] = to_int_number(spec_value(specs, "Key Specs", "Color Support")) or spec_value(specs, "Display", "Color Support")
    internal["display"]["color_gamut"] = spec_list(specs, "Key Specs", "Color Gamut") or spec_value(specs, "Display", "Color Gamut")
    # spec_list(specs, "Key Specs", "Finish") -> Anti-Glare -> using full web search
    internal["display"]["touchscreen"] = match_any(spec_value(specs, "Key Specs", "Touchscreen"), ["yes"])
    internal["display"]["aspect_ratio"] = spec_value(specs, "Display", "Aspect Ratio")
    internal["display"]["static_contrast_ratio"] = spec_value(specs, "Display", "Contrast Ratio")
    internal["display"]["adjustment"]["height"] = match_any(spec_value(specs, "General", "Adjustments"), ["height"])
    internal["display"]["adjustment"]["pivot"] = match_any(spec_value(specs, "General", "Adjustments"), ["pivot", "rotation"])
    internal["display"]["adjustment"]["swivel"] = match_any(spec_value(specs, "General", "Adjustments"), ["swivel"])
    internal["display"]["adjustment"]["tilt"] = match_any(spec_value(specs, "General", "Adjustments"), ["tilt"])


    internal["display"]["brightness_cdm2"] = extract_number(spec_value(specs, "Display", "Maximum Brightness"))
    # spec_value(specs, "Display", "Contrast Ratio")
    internal["display"]["refresh_rate_hz"] = extract_number(spec_value(specs, "Display", "Refresh Rate"))
    internal["display"]["features"] = spec_list(specs, "Display", "Variable Refresh Technology")

    def viewing_angle(value: str, index: int) -> str:
        parts = value.replace("°", "").split("x")
        return f"{parts[index].strip()}°" if len(parts) == 2 else ""

    value = spec_value(specs, "Display & Graphics", "Viewing Angle (H x V)")
    internal["display"]["horizontal_viewing_angle"] = viewing_angle(value, 0)
    internal["display"]["vertical_viewing_angle"] = viewing_angle(value, 1)
    internal["display"]["curve_screen"] = match_any(spec_value(specs, "Display", "Curved Display"), ["yes"])

    # io
    internal["io"]["ports"] = spec_list(specs, "Key Specs", "A/V Inputs") + spec_list(specs, "Key Specs", "A/V Outputs") + spec_list(specs, "Key Specs", "USB I/O")

    # audio
    internal["audio"]["speaker"] = match_any(spec_value(specs, "Key Specs", "Built-In Speakers"), ["yes"])

    #technical
    internal["technical"]["vesa_mount"] = match_any(spec_value(specs, "General", "VESA Mounting-Hole Pattern"), ["*"])
    internal["technical"]["vesa_mount_size"] = [s.replace(" mm", "") for s in spec_list(specs, "General", "VESA Mounting-Hole Pattern")]

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
    # internal["io"]["ports"] = spec_list(specs, "CONNECTIVITY", "USB I/O")

    return internal
