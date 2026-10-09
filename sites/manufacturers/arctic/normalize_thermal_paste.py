"""Arctic → internal for CPU AIO / thermal interface products."""

from __future__ import annotations

import re

from core.schema.registry import empty_internal
from core.spec_lookup import extract_number, spec_list, spec_value
from core.units import length_to_in, weight_to_lb
from sites.cdw._common import fill_identity_content


def _packaging_dims(specs: dict) -> dict[str, str]:
    out: dict[str, str] = {}

    for label, field in (("Width", "width_in"), ("Height", "height_in"), ("Length", "length_in"),
                         ("Weight", "package_lb"),):
        val = spec_value(specs, "Packaging", label, match_suffix=True, )

        if not val:
            continue

        if field == "package_lb":
            out[field] = weight_to_lb(val)
        else:
            out[field] = length_to_in(val)

    return out


def _current_and_voltage(value: str) -> tuple[str, str]:
    if not value:
        return "", ""

    current, separator, voltage = value.partition("|")

    return (extract_number(current), extract_number(voltage) if separator else "",)


def _labelled_dimensions_to_in(value: str) -> dict[str, str]:
    """Parse Arctic combined dimensions.

    Examples:
        83 (L) x 108 (W) x 136 (H) mm
        83(L) x 108(W) x 136(H) mm
    """
    if not value:
        return {}

    value = str(value).strip()

    unit = "mm" if re.search(r"\bmm\b", value, re.I) else ""

    matches = re.findall(r"(\d+(?:\.\d+)?)\s*\(([LWH])\)", value, re.I, )

    fields = {"L": "length_in", "W": "width_in", "H": "height_in", }

    return {fields[label.upper()]: length_to_in(number, unit) for number, label in matches}


def _separate_dimensions_to_in(specs: dict) -> dict[str, str]:
    """Parse Arctic dimensions stored as separate fields.

    Supports:
        General Specifications
          Length: 86 mm
          Width: 109 mm
          Height: 137 mm

    and:
        General Specifications
          Size & Weight
            Length: 86 mm
            Width: 109 mm
            Height: 137 mm
    """
    result: dict[str, str] = {}

    fields = {
        "Length": "length_in",
        "Width": "width_in",
        "Height": "height_in",
    }

    for source_key, output_key in fields.items():

        value = (
            spec_value(
                specs,
                ["General Specifications", "Size & Weight", source_key],
            )
            or
            spec_value(
                specs,
                ["General Specifications", source_key],
            )
        )

        if value:
            result[output_key] = length_to_in(str(value), "mm")

    return result


def _item_dimensions_to_in(specs: dict) -> dict[str, str]:
    """Support both Arctic item-dimension formats."""
    combined = spec_value(
        specs,
        ["General Specifications", "Dimensions"],
    )

    if combined:
        dimensions = _labelled_dimensions_to_in(combined)

        if dimensions:
            return dimensions

    return _separate_dimensions_to_in(specs)


def _weight_to_lb(value) -> str:
    """Convert Arctic item weight to pounds.

    Unitless Arctic item weight is treated as grams.
    """
    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    if re.search(r"\bkg\b", value, re.I):
        return weight_to_lb(value)

    if re.search(r"\bg\b", value, re.I):
        return weight_to_lb(value)

    # Arctic case: bare item weight is grams.
    return weight_to_lb(f"{value} g")

def normalize_arctic_thermal_paste(raw: dict, *, product_code: str = "THERMAL-PASTE", sub_code: str = "THERMAL-PASTE") -> dict:
    specs = raw.get("specs") or {}
    title = str(raw.get("title") or "").strip()

    internal = empty_internal(product_code)

    fill_identity_content(internal, raw=raw, cdw=raw, specs=specs, spec_value=spec_value, )

    # Identity
    internal["identity"]["brand"] = (internal["identity"].get("brand") or "Arctic")
    internal["identity"]["product_type"] = "Thermal Paste"
    internal["identity"]["title"] = title
    internal["identity"]["model"] = raw.get("mpn") or ""

    # Cooling
    internal["cooling"]["continuous_use_temperature"] = spec_value(specs, ["General Specifications", "Continuous Use Temperature"])

    internal["density"] = spec_value(specs, ["General Specifications", "Density"])
    internal["viscosity"] = spec_value(specs, ["General Specifications", "Viscosity"])
    internal["volume_resistivity"] = spec_value(specs, ["General Specifications", "Volume Resistivity"])
    internal["breakdown_voltage"] = spec_value(specs, ["General Specifications", "Breakdown Voltage"])
    internal["colour"] = spec_value(specs, ["General Specifications", "Colour"])

    # Item dimensions
    item_dims = _item_dimensions_to_in(specs)

    internal["physical"]["dimensions"]["item"].update(item_dims)

    # Item weight
    item_weight = (
            spec_value(
                specs,
                ["General Specifications", "Size & Weight", "Weight"],
            )
            or
            spec_value(
                specs,
                ["General Specifications", "Weight"],
            )
            or
            spec_value(
                specs,
                ["General Specifications", "Net Weight"],
            )
    )

    item_weight_lb = _weight_to_lb(item_weight)

    if item_weight_lb:
        internal["physical"]["weight"]["item_lb"] = item_weight_lb

    # Included items
    internal["included_items"] = [value for value in
                                  [spec_value(specs, ["General Specifications", "TIM", ], ),  # 2nd case
                                   spec_value(specs, ["General Specifications", "CPU Specifications", "Thermal Compound"])]
                                  if value]

    # Packaging
    dims = _packaging_dims(specs)

    if dims.get("length_in"):
        internal["physical"]["dimensions"]["package"]["length_in"] = dims["length_in"]

    if dims.get("width_in"):
        internal["physical"]["dimensions"]["package"]["width_in"] = dims["width_in"]

    if dims.get("height_in"):
        internal["physical"]["dimensions"]["package"]["height_in"] = dims["height_in"]

    if dims.get("package_lb"):
        internal["physical"]["weight"]["package_lb"] = (dims["package_lb"])

    # UPC
    for group in specs.values():
        if not isinstance(group, dict):
            continue

        for key, val in group.items():
            if re.match(r"^UPC", str(key), re.I):
                internal["identity"]["upc"] = (internal["identity"].get("upc") or str(val).strip())

            # if re.match(r"^EAN", str(key), re.I):  #     internal["identity"]["ean"] = (  #         internal["identity"].get("ean")  #         or str(val).strip()  #     )

    internal.setdefault("_meta", {})["sub_code"] = sub_code

    return internal
