"""Arctic → internal for CPU AIO / thermal interface products (sub_code CPU-AIO)."""

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
        val = spec_value(specs, "Packaging", label, match_suffix=True)
        if not val:
            continue
        if field == "package_lb":
            out[field] = weight_to_lb(val)
        else:
            out[field] = length_to_in(val)
    return out


def _current_and_voltage(value: str) -> tuple[str, str]:
    current, separator, voltage = value.partition("|")
    return extract_number(current), extract_number(voltage) if separator else ""


def _labelled_dimensions_to_in(value: str) -> dict[str, str]:
    """Parse Arctic values such as ``317 (L) x 138 (W) x 38 (H) mm``."""
    unit = "mm" if "mm" in value.lower() else ""
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*\(([LWH])\)", value, re.I)
    fields = {"L": "length_in", "W": "width_in", "H": "height_in"}
    return {fields[label.upper()]: length_to_in(number, unit) for number, label in matches}


def _tube_diameter_mm(value: str | None) -> dict[str, str]:
    result = {
        "outer_mm": "",
        "inner_mm": "",
    }

    if not value:
        return result

    value = str(value)

    outer = re.search(r"outer:\s*(\d+(?:\.\d+)?)\s*mm?", value, re.I)
    inner = re.search(r"inner:\s*(\d+(?:\.\d+)?)\s*mm?", value, re.I)

    if outer or inner:
        result["outer_mm"] = outer.group(1) if outer else ""
        result["inner_mm"] = inner.group(1) if inner else ""
    else:
        # Fallback: value is just a number (e.g. "12.4")
        m = re.search(r"\d+(?:\.\d+)?", value)
        if m:
            result["outer_mm"] = m.group(0)

    return result

def _airflow_values(value: str) -> tuple[str, str]:
    cfm = re.search(r"(\d+(?:\.\d+)?)\s*cfm", value, re.I)
    m3h = re.search(r"(\d+(?:\.\d+)?)\s*m(?:³|3)\s*/\s*h", value, re.I)
    return (cfm.group(1) if cfm else "", m3h.group(1) if m3h else "")

def fan_name(text: str) -> str:
    if not text:
        return ""

    return re.sub(r"^\s*\d+\s*x\s*", "", text, flags=re.IGNORECASE).strip()


def number_of_fan(text: str) -> str:
    if not text:
        return ""

    match = re.search(r"(\d+)\s*x", text, re.IGNORECASE)
    return match.group(1) if match else ""

def fan_size(text: str) -> str:
    if not text:
        return ""

    match = re.search(r"\b(?:P|PS|Z)(\d{2})\b", text, re.IGNORECASE)
    return match.group(1) if match else ""


def maximum_rpm(text: str) -> str:
    if not text:
        return ""

    numbers = re.findall(r"\d+", text)
    return numbers[-1] if numbers else ""


def minimum_rpm(text: str) -> str:
    if not text:
        return ""

    numbers = re.findall(r"\d+", text)
    return numbers[0] if numbers else ""

def warranty_to_days(text: str) -> str:
    if not text:
        return ""

    text = text.lower()

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

    match = re.search(r"\b(120|140|240|280|360|420)\b", text)
    return match.group(1) if match else ""

def normalize_arctic_cpu_aio(
    raw: dict,
    *,
    product_code: str = "CPU-AIO",
    sub_code: str = "CPU-AIO",
) -> dict:
    specs = raw.get("specs") or {}
    title = raw.get("title") or ""

    internal = empty_internal(product_code)

    fill_identity_content(
        internal,
        raw=raw,
        cdw=raw,
        specs=specs,
        spec_value=spec_value,
    )
    internal["identity"]["brand"] = internal["identity"].get("brand") or "Arctic"
    internal["identity"]["product_type"] = "CPU AIO Cooler"
    internal["identity"]["title"] = title
    internal["identity"]["model"] =  raw.get("mpn") or ""

    internal["cooling"]["operating_ambient_temperature"] = spec_value(specs, ["General Specifications", "Operating Ambient Temperature"])
    pump = spec_value(specs, ["General Specifications", "Pump"])
    internal["cooling"]["pump"] = {
        "description": pump,
        "min_rpm": minimum_rpm(pump) or extract_number(spec_value(specs, ["General Specifications", "Pump/Tubing Specifications", "Min rpm"])),
        "max_rpm": maximum_rpm(pump) or extract_number(spec_value(specs, ["General Specifications",  "Pump/Tubing Specifications", "Max rpm"])),
    }
    internal["cooling"]["cold_plate"] = spec_list(specs, ["General Specifications", "Cold Plate"])
    internal["cooling"]["tube_diameter"] = _tube_diameter_mm(spec_value(specs, ["General Specifications", "Tube Diameter"]))

    # Fill missing values from dedicated fields if present.
    internal["cooling"]["tube_diameter"]["outer_mm"] = (
            spec_value(specs, ["General Specifications", "Pump/Tubing Specifications", "Tube Outer Diameter"])
            or internal["cooling"]["tube_diameter"]["outer_mm"]
    )

    internal["cooling"]["tube_diameter"]["inner_mm"] = (
            spec_value(specs, ["General Specifications", "Pump/Tubing Specifications", "Tube Inner Diameter"])
            or internal["cooling"]["tube_diameter"]["inner_mm"]
    )

    internal["cooling"]["tube_diameter"]["length_mm"] = (
            extract_number(spec_value(specs, ["General Specifications", "Tube Length"]))
            or extract_number(spec_value(specs, ["General Specifications", "Pump/Tubing Specifications", "Tube Length"]))
    )

    internal["compatibility"]["intel"] = spec_list(specs, ["General Specifications", "Compatibility", "Intel"]) or spec_list(specs, ["General Specifications", "CPU Specifications", "Intel Socket"])
    internal["compatibility"]["amd"] = spec_list(specs, ["General Specifications", "Compatibility", "AMD"]) or spec_list(specs, ["General Specifications", "CPU Specifications", "AMD Socket"])
    internal["compatibility"]["pi_nnpi"] = spec_list(specs, ["General Specifications", "Compatibility", "PI | NNPI"])

    internal["radiator"]["size"] = radiator_size(title)
    radiator_dimensions = spec_value(specs, ["General Specifications", "Radiator", "Dimensions"])
    internal["radiator"]["material"] = spec_value(specs, ["General Specifications", "Radiator", "Material"])
    internal["radiator"]["dimension"].update(_labelled_dimensions_to_in(radiator_dimensions))

    cooling_current, cooling_voltage = _current_and_voltage(spec_value(specs, ["General Specifications", "Pump Current | Voltage"])) or _current_and_voltage(spec_value(specs, ["General Specifications", "Pump/Tubing Specifications", "Current | Voltage"]))
    internal["cooling"]["current_a"] = cooling_current
    internal["cooling"]["voltage_v"] = cooling_voltage

    radiator_fan_general = spec_value(specs, ["General Specifications", "Radiator Fan","General"])
    radiator_fan_speed = (
            spec_value(specs, ["General Specifications", "Radiator Fan", "Speed"])
            or spec_value(specs, ["General Specifications", "Fan Specifications", "Fan Speed"])
    )
    fan_count = number_of_fan(radiator_fan_general)
    internal["radiator_fan"]["fan"] = {
        "number_of_fan": (
            fan_count
            if fan_count not in (None, "")
            else spec_value(specs, ["General Specifications", "Fan Specifications", "Fan Speed"])
        ),
        "size_cm": fan_size(radiator_fan_general),
        "min_rpm": minimum_rpm(radiator_fan_speed),
        "max_rpm": maximum_rpm(radiator_fan_speed),
    }

    airflow_cfm, airflow_m3h = _airflow_values(spec_value(specs, ["General Specifications", "Radiator Fan", "Airflow"]) or spec_value(specs, ["General Specifications", "Fan Specifications", "Airflow | Airflow"]))
    internal["radiator_fan"]["airflow_cfm"] = airflow_cfm
    internal["radiator_fan"]["airflow_m3h"] = airflow_m3h
    internal["radiator_fan"]["static_pressure_mmh2o"] = extract_number(spec_value(specs, ["General Specifications", "Radiator Fan", "Static Pressure"]) or spec_value(specs, ["General Specifications", "Fan Specifications", "Static Pressure"]))
    internal["radiator_fan"]["bearing"] = spec_value(specs, ["General Specifications", "Radiator Fan", "Bearing"]) or spec_value(specs, ["General Specifications", "Fan Specifications", "Bearing"])
    fan_current, fan_voltage = _current_and_voltage(spec_value(specs, ["General Specifications", "Radiator Fan", "Bearing Current | Voltage"])) or _current_and_voltage(spec_value(specs, ["General Specifications", "Fan Specifications", "Bearing Current | Voltage"]))
    internal["radiator_fan"]["current_a"] = fan_current
    internal["radiator_fan"]["voltage_v"] = fan_voltage
    internal["radiator_fan"]["connector"] = spec_value(specs, ["General Specifications", "Radiator Fan", "Connector"]) or spec_value(specs, ["General Specifications", "Fan Specifications", "Connector"])

    vrm_fan = spec_value(specs, ["General Specifications", "VRM Module", "VRM Fan"]) or spec_value(specs, ["General Specifications", "Fan Specifications", "Fan Speed"])
    internal["vrm_module"]["vrm_fan"] = {
        "description": vrm_fan,
        "min_rpm": minimum_rpm(vrm_fan),
        "max_rpm": maximum_rpm(vrm_fan)
    }


    vrm_current, vrm_voltage = _current_and_voltage(spec_value(specs, ["General Specifications",  "VRM Module", "VRM Fan Current | Voltage"]))
    internal["vrm_module"]["current_a"] = vrm_current
    internal["vrm_module"]["voltage_v"] = vrm_voltage

    internal["rgb"]["leds"] = spec_value(specs, ["General Specifications", "RGB", "LEDs"])
    rgb_current, rgb_voltage = _current_and_voltage(spec_value(specs, ["General Specifications", "RGB", "LEDs Current | Voltage"]))
    internal["rgb"]["current_a"] = rgb_current
    internal["rgb"]["voltage_v"] = rgb_voltage
    internal["rgb"]["connector"] = spec_value(specs, ["General Specifications", "RGB", "Connector"])

    item_dims = _labelled_dimensions_to_in(radiator_dimensions)
    internal["physical"]["dimensions"]["item"].update(item_dims)
    internal["physical"]["weight"]["item_lb"] = weight_to_lb(spec_value(specs, ["General Specifications", "Weight"]))

    internal["warranty"] = warranty_to_days(spec_value(specs, ["General Specifications", "Warranty"]))

    internal["included_items"] = [
        p for p in [
            spec_value(specs, ["General Specifications", "TIM"]),
            spec_value(specs, ["General Specifications", "CPU Specifications Thermal Compound"]),
        ] if p
    ]

    dims = _packaging_dims(specs)
    if dims.get("length_in"):
        internal["physical"]["dimensions"]["package"]["length_in"] = dims["length_in"]
    if dims.get("width_in"):
        internal["physical"]["dimensions"]["package"]["width_in"] = dims["width_in"]
    if dims.get("height_in"):
        internal["physical"]["dimensions"]["package"]["height_in"] = dims["height_in"]
    if dims.get("package_lb"):
        internal["physical"]["weight"]["package_lb"] = dims["package_lb"]

    for group in specs.values():
        if not isinstance(group, dict):
            continue
        for key, val in group.items():
            if re.match(r"^UPC", str(key), re.I):
                internal["identity"]["upc"] = internal["identity"].get("upc") or str(val).strip()
            # if re.match(r"^EAN", str(key), re.I):
            #     internal["identity"]["ean"] = internal["identity"].get("ean") or str(val).strip()
    # internal.setdefault("_meta", {})["sub_code"] = sub_code
    return internal
