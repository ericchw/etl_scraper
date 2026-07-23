"""Arctic → internal for CPU AIO / thermal interface products (sub_code CPU-AIO)."""

from __future__ import annotations

import re

from core.schema.registry import empty_internal
from core.units import length_to_in, weight_to_lb
from sites.cdw._common import fill_identity_content


def _spec_value(specs: dict, group: str, key: str) -> str:
    block = specs.get(group) or {}
    if not isinstance(block, dict):
        return ""
    return str(block.get(key) or "").strip()


def _packaging_dims(specs: dict) -> dict[str, str]:
    pkg = specs.get("Packaging") or specs.get("General Specifications") or {}
    if not isinstance(pkg, dict):
        return {}
    out: dict[str, str] = {}
    for label, field in (
        ("Width", "width_in"),
        ("Height", "height_in"),
        ("Length", "length_in"),
        ("Weight", "package_lb"),
    ):
        val = str(pkg.get(label) or "").strip()
        if not val:
            continue
        if field == "package_lb":
            out[field] = weight_to_lb(val)
        else:
            out[field] = length_to_in(val)
    return out


def normalize_arctic_cpu_aio(
    raw: dict,
    *,
    product_code: str = "ACC",
    sub_code: str = "CPU-AIO",
) -> dict:
    specs = raw.get("specs") or {}
    internal = empty_internal(product_code)

    fill_identity_content(
        internal,
        raw=raw,
        cdw=raw,
        specs=specs,
        spec_value=_spec_value,
    )
    internal["identity"]["brand"] = internal["identity"].get("brand") or "Arctic"
    internal["identity"]["product_type"] = (
        internal["identity"].get("product_type") or "Thermal Interface Material"
    )

    general = specs.get("General Specifications") or specs.get("General") or {}
    if isinstance(general, dict):
        internal["cooling"]["Thermal Interface Material"] = general.get("TIM", "")
        internal["cooling"]["viscosity"] = general.get("Viscosity", "")
        internal["cooling"]["volume_resistivity"] = general.get("Volume Resistivity", "")
        internal["cooling"]["continuous_use_temperature"] = general.get(
            "Continuous Use Temperature", ""
        )
        internal["cooling"]["thermal_conductivity"] = general.get("Thermal Conductivity", "")
        internal["cooling"]["colour"] = general.get("Colour") or general.get("Color", "")

    title = str(raw.get("title") or "").upper()
    if "AIO" in title or "LIQUID" in title:
        internal["cooling"]["product_type"] = "CPU AIO Cooler"
    elif "PASTE" in title or "MX-" in title:
        internal["cooling"]["product_type"] = "Thermal Paste"

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
            if re.match(r"^EAN|^UPC", key, re.I):
                internal["identity"]["upc"] = internal["identity"].get("upc") or str(val).strip()

    internal.setdefault("_meta", {})["sub_code"] = sub_code
    return internal
