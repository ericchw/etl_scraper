"""Arctic → internal for CPU AIO / thermal interface products."""

from __future__ import annotations

import re

from core.schema.registry import empty_internal
from core.spec_lookup import extract_number, spec_list, spec_value
from core.units import length_to_in, weight_to_lb
from sites.cdw._common import fill_identity_content


def _packaging_dims(specs: dict) -> dict[str, str]:
    out: dict[str, str] = {}

    for label, field in (
        ("Width", "width_in"),
        ("Height", "height_in"),
        ("Length", "length_in"),
        ("Weight", "package_lb"),
    ):
        val = spec_value(
            specs,
            "Packaging",
            label,
            match_suffix=True,
        )

        if not val:
            continue

        if field == "package_lb":
            out[field] = weight_to_lb(val)
        else:
            out[field] = length_to_in(val)

    # Fan size
    #
    # Example:
    # Length: 120 mm
    # -> fan.size_cm = "12"
    #
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


def _airflow_values(value: str) -> tuple[str, str]:
    if not value:
        return "", ""

    cfm = re.search(r"(\d+(?:\.\d+)?)\s*cfm", value, re.I, )

    m3h = re.search(r"(\d+(?:\.\d+)?)\s*m(?:³|3)\s*/\s*h", value, re.I, )

    return (cfm.group(1) if cfm else "", m3h.group(1) if m3h else "",)


def fan_name(text: str) -> str:
    if not text:
        return ""

    return re.sub(r"^\s*\d+\s*x\s*", "", text, flags=re.IGNORECASE, ).strip()


def number_of_fan(text: str) -> str:
    if not text:
        return ""

    match = re.search(r"(\d+)\s*x", text, re.IGNORECASE, )

    return match.group(1) if match else "1"


def fan_size(text: str) -> str:
    if not text:
        return ""

    match = re.search(r"\b(?:P|PS|Z)(\d{2})\b", text, re.IGNORECASE, )

    return match.group(1) if match else ""

def length_to_cm(value: str) -> str:
    """
    Convert a length value to centimeters.

    Examples:
        "120 mm" -> "12"
        "12 cm"  -> "12"
        "1.2 m"  -> "120"
        "4 in"   -> "10.16"
    """
    if not value:
        return ""

    value = str(value).strip().lower()

    # Extract numeric portion and unit
    import re

    match = re.search(r"([-+]?\d*\.?\d+)\s*([a-z\"]+)?", value)
    if not match:
        return ""

    number = float(match.group(1))
    unit = (match.group(2) or "cm").strip()

    conversions = {
        "mm": 0.1,
        "millimeter": 0.1,
        "millimeters": 0.1,
        "cm": 1,
        "centimeter": 1,
        "centimeters": 1,
        "m": 100,
        "meter": 100,
        "meters": 100,
        "in": 2.54,
        "inch": 2.54,
        "inches": 2.54,
        '"': 2.54,
    }

    multiplier = conversions.get(unit)
    if multiplier is None:
        return ""

    result = number * multiplier

    # Avoid "12.0"
    if result.is_integer():
        return str(int(result))

    return str(round(result, 4))

def in_to_cm(value: str) -> str:
    if not value:
        return ""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return ""
    return str(round(n * 2.54, 1))

def _rpm_range(text: str):
    if not text:
        return None

    match = re.search(
        r"(\d+)\s*[–-]\s*(\d+)\s*rpm\b",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    a = int(match.group(1))
    b = int(match.group(2))

    return min(a, b), max(a, b)

def maximum_rpm(text: str) -> str:
    result = _rpm_range(text)
    return str(result[1]) if result else ""

def minimum_rpm(text: str) -> str:
    result = _rpm_range(text)
    return str(result[0]) if result else ""


def warranty_to_days(text: str) -> str:
    if not text:
        return ""

    text = str(text).lower()

    years = re.search(r"(\d+)\s*year", text)
    if years:
        return str(int(years.group(1)) * 365)

    months = re.search(r"(\d+)\s*month", text)
    if months:
        return str(int(months.group(1)) * 30)

    days = re.search(r"(\d+)\s*day", text)
    if days:
        return str(int(days.group(1)))

    return ""


def radiator_size(text: str) -> str:
    if not text:
        return ""

    match = re.search(r"\b(120|140|240|280|360|420)\b", text, )

    return match.group(1) if match else ""


def parse_heatsink_fins(value):
    """
    Parse heatsink fin specification such as:
        '46x 0.4 mm Aluminium Fins'

    Returns:
        {
            "fin_material": "Aluminium",
            "number_of_fins": 46,
            "fim_thickness_mm": 0.4,
        }
    """
    if not value:
        return {"fin_material": "", "number_of_fins": "", "fim_thickness_mm": "", }

    value = str(value).strip()

    # Number of fins + thickness
    match = re.search(r'(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm\s+(.+?)\s+fins?\b', value, re.IGNORECASE, )

    if not match:
        return {"fin_material": "", "number_of_fins": "", "fim_thickness_mm": "", }

    number_of_fins = int(match.group(1))
    fin_thickness_mm = float(match.group(2))
    fin_material = match.group(3).strip()

    return {"fin_material": fin_material, "number_of_fins": number_of_fins, "fim_thickness_mm": fin_thickness_mm, }


def extract_fan_dimensions(value):
    if not value:
        return None, None, None

    text = str(value)

    # Dimensions:
    # 100 (L) x 100 (W) x 25 (H) mm
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*\(L\)\s*x\s*"
        r"(\d+(?:\.\d+)?)\s*\(W\)\s*x\s*"
        r"(\d+(?:\.\d+)?)\s*\(H\)\s*"
        r"(mm|cm|in|inch|inches)",
        text,
        re.IGNORECASE
    )

    if not match:
        return None, None, None

    length = float(match.group(1))
    width = float(match.group(2))
    height = float(match.group(3))
    unit = match.group(4).lower()

    # Convert everything to cm
    if unit == "mm":
        length /= 10
        width /= 10
        height /= 10
    elif unit in ("in", "inch", "inches"):
        length *= 2.54
        width *= 2.54
        height *= 2.54

    return length, width, height


def normalize_arctic_case_fan(raw: dict, *, product_code: str = "CASE-FAN",
                                  sub_code: str = "CASE-FAN", ) -> dict:
    specs = raw.get("specs") or {}
    title = raw.get("title") or ""

    internal = empty_internal(product_code)

    fill_identity_content(internal, raw=raw, cdw=raw, specs=specs, spec_value=spec_value, )

    # Identity
    internal["identity"]["brand"] = (internal["identity"].get("brand") or "Arctic")
    internal["identity"]["product_type"] = "Case Fan"
    internal["identity"]["title"] = title
    internal["identity"]["model"] = raw.get("mpn") or ""

    # Cooling
    internal["cooling"]["operating_ambient_temperature"] = spec_value(specs, ["General Specifications",
                                                                              "Operating Ambient Temperature"], )

    # Fan
    internal["fan"]["number_of_fan"] = ""
    fan_speed = (spec_value(specs, ["General Specifications", "Fan", "Speed"]) or
                 spec_value(specs, ["General Specifications", "Fans", "Speed"]) or
                 spec_value(specs,["General Specifications", "Fan Specifications", "Speed"]) or
                 spec_value(specs, ["General Specifications", "Fan Specifications", "Fan Speed"])
    )
    internal["fan"]["min_rpm"] = minimum_rpm(fan_speed)
    internal["fan"]["max_rpm"] = maximum_rpm(fan_speed)

    airflow_cfm, airflow_m3h = _airflow_values(
        spec_value(specs, ["General Specifications", "Performance", "Airflow"])
        or spec_value(specs,["General Specifications", "Fan Specifications", "Airflow"])
    )
    internal["fan"]["airflow_cfm"] = airflow_cfm
    internal["fan"]["airflow_m3h"] = airflow_m3h

    internal["fan"]["bearing"] = (spec_value(specs, ["General Specifications", "Fan", "Fan Bearing"]) or
                                    spec_value(specs, ["General Specifications", "Fans", "Bearing"]) or
                                  spec_value(specs, ["General Specifications", "Fan Specifications", "Bearing"]) or
                                    spec_value(specs, ["General Specifications", "Fan Specifications", "Fan Bearing"])
    )
    internal["fan"]["cable_length"] = spec_value(specs, ["General Specifications", "Fans", "Cable Length"]
    )
    internal["fan"]["noise_level"] = (spec_value(specs, ["General Specifications", "Performance", "Noise Level"]) or
                                      spec_value(specs, ["General Specifications", "Fan", "Noise Level"]) or
                                      spec_value(specs, ["General Specifications", "Fans", "Noise Level"])
                                    )

    # Current / Voltage
    current_voltage = (spec_value(specs, ["General Specifications", "Fan", "Current | Voltage"]) or
                       spec_value(specs, ["General Specifications", "Fans", "Current | Voltage"]) or
                       spec_value(specs, ["General Specifications", "Electric Characteristics", "Current | Voltage"])
                       )

    if not current_voltage:
        current_voltage = (spec_value(specs, ["General Specifications", "Fan Specifications", "Current | Voltage"]) or
                           spec_value(specs, ["General Specifications", "Fans", "Current | Voltage"])
                           )

    fan_current, fan_voltage = _current_and_voltage(current_voltage)

    internal["fan"]["current_a"] = (
            fan_current
            or extract_number(spec_value(specs, ["General Specifications", "Fan", "Current"]))
            or extract_number(spec_value(specs, ["General Specifications", "Fans", "Current"]))
            or extract_number(spec_value(specs, ["General Specifications", "Fans Specifications", "Current"]))
    )

    internal["fan"]["voltage_v"] = (
            fan_voltage
            or extract_number(spec_value(specs, ["General Specifications", "Fan", "Voltage"]))
            or extract_number(spec_value(specs, ["General Specifications", "Fans", "Voltage"]))
            or extract_number(spec_value(specs, ["General Specifications", "Fans Specifications", "Voltage"]))
    )

    internal["fan"]["connector"] = (
            spec_value(specs, ["General Specifications", "Fan", "Connector"])
            or spec_value(specs, ["General Specifications", "Fans", "Connector"])
            or spec_value(specs, ["General Specifications", "Fan Specifications", "Connector"])
    )

    # RGB
    internal["rgb"]["leds"] = spec_value(specs, ["General Specifications", "RGB", "LEDs"]) or spec_value(specs, ["General Specifications", "RGB Specifications", "LEDs"])
    rgb_current_voltage = spec_value(specs, ["General Specifications", "RGB", "Current | Voltage"]) or spec_value(specs, ["General Specifications", "RGB Specifications", "Current | Voltage"])
    rgb_current, rgb_voltage = _current_and_voltage(rgb_current_voltage)
    internal["rgb"]["current_a"] = (rgb_current or extract_number(spec_value(specs, ["General Specifications", "RGB", "Current"])))
    internal["rgb"]["voltage_v"] = (rgb_voltage or extract_number(spec_value(specs, ["General Specifications", "RGB", "Voltage"])))
    internal["rgb"]["cable_length"] = (rgb_voltage or extract_number(spec_value(specs, ["General Specifications", "RGB", "Cable Length"])))
    internal["rgb"]["connector"] = spec_value(specs, ["General Specifications", "RGB", "Connector"])

    # Item dimensions
    item_dims = _item_dimensions_to_in(specs)


    internal["physical"]["dimensions"]["item"].update(item_dims)

    internal["fan"]["size_cm"] = (
            length_to_cm(spec_value(specs, ["General Specifications", "Size & Weight", "Length"]))
            or in_to_cm(item_dims.get("length_in"))
    )

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

    # Warranty
    internal["warranty"] = warranty_to_days(spec_value(specs, ["General Specifications", "Warranty", ], ))

    # Included items
    internal["included_items"] = [value for value in
                                  [spec_value(specs, ["General Specifications", "TIM", ], ),  # 2nd case
                                   spec_value(specs, ["General Specifications", "CPU Specifications",
                                                      "Thermal Compound", ], ), ] if value]

    # Packaging
    dims = _packaging_dims(specs)

    if dims.get("length_in"):
        internal["physical"]["dimensions"]["package"]["length_in"] = (
            dims["length_in"]
        )

    if dims.get("width_in"):
        internal["physical"]["dimensions"]["package"]["width_in"] = (
            dims["width_in"]
        )

    if dims.get("height_in"):
        internal["physical"]["dimensions"]["package"]["height_in"] = (
            dims["height_in"]
        )

    if dims.get("package_lb"):
        internal["physical"]["weight"]["package_lb"] = (
            dims["package_lb"]
        )

    # UPC
    for group in specs.values():
        if not isinstance(group, dict):
            continue

        for key, val in group.items():
            if re.match(r"^UPC", str(key), re.I):
                internal["identity"]["upc"] = (internal["identity"].get("upc") or str(val).strip())

            # if re.match(r"^EAN", str(key), re.I):  #     internal["identity"]["ean"] = (  #         internal["identity"].get("ean")  #         or str(val).strip()  #     )

    # internal.setdefault("_meta", {})["sub_code"] = sub_code

    return internal

# if __name__ == "__main__":
#     print(minimum_rpm("200 - 1800 rpm, PWM Controlled (0 rpm below 5 % PWM)"))