"""Shared B&H packaging / spec helpers."""

from __future__ import annotations

import re

from core.spec_lookup import spec_value
from core.units import length_to_in, weight_to_lb


def _spec_val(specs: dict, *groups_and_keys: tuple[str, str]) -> str:
    for group, key in groups_and_keys:
        block = specs.get(group) or {}
        if isinstance(block, dict):
            val = block.get(key)
            if val:
                return str(val).strip()
    return ""


def _find_packaging(specs: dict) -> dict[str, str]:
    found: dict[str, str] = {}
    for group, entries in (specs or {}).items():
        if not isinstance(entries, dict):
            continue
        for key, val in entries.items():
            if not val:
                continue
            combined = f"{group} {key}".lower()
            text = str(val).strip()
            if "weight" in combined and "package" not in found:
                if "weight" in combined or "shipping" in combined:
                    found["weight"] = text
            if "length" in key.lower():
                found.setdefault("length", text)
            if "width" in key.lower():
                found.setdefault("width", text)
            if "height" in key.lower() or "depth" in key.lower():
                found.setdefault("height", text)
    return found

def fill_bh_packaging(
    internal: dict,
    specs: dict,
    *,
    dim_unit: str = "in",
    weight_unit: str = "lb",
) -> None:
    pkg_block = specs.get("Package Dimensions") or {}
    packaging = _find_packaging(specs)
    print(f"DEBUG fill_bh_packaging pkg_block: {pkg_block}")
    print(f"DEBUG fill_bh_packaging packaging: {packaging}")


    length = (
        _spec_val(specs, ("Package Dimensions", "Length"))
        or packaging.get("length", "")
    )
    width = (
        _spec_val(specs, ("Package Dimensions", "Width"))
        or packaging.get("width", "")
    )
    height = (
        _spec_val(specs, ("Package Dimensions", "Height"))
        or packaging.get("height", "")
    )
    weight = (
        _spec_val(specs, ("Package Dimensions", "Weight"))
        or packaging.get("weight", "")
        or _spec_val(specs, ("Packaging Info", "Package Weight"))
        or _spec_val(specs, ("Packaging Info", "Weight"))
        or _spec_val(specs, ("Shipping", "Weight"))
    )

    print(f"DEBUG fill_bh_packaging length, width, height, weight: {length}, {width}, {height}, {weight}")

    box_dims = _spec_val(specs, ("Packaging Info", "Box Dimensions (LxWxH)"))
    print(f"DEBUG fill_bh_packaging box_dims: {box_dims}")

    if box_dims and not (length and width and height):
        match = re.search(
            r"([\d.]+)\s*[x×]\s*([\d.]+)\s*[x×]\s*([\d.]+)",
            box_dims,
            re.I,
        )
        if match:
            length = length or match.group(1)
            width = width or match.group(2)
            height = height or match.group(3)

    if isinstance(pkg_block, dict):
        length = length or str(pkg_block.get("Length", "")).strip()
        width = width or str(pkg_block.get("Width", "")).strip()
        height = height or str(pkg_block.get("Height", "")).strip()
        weight = weight or str(pkg_block.get("Weight", "")).strip()


    print(f"DEBUG fill_bh_packaging length, width, height, weight: {length}, {width}, {height}, {weight}")

    internal["physical"]["dimensions"]["package"]["length_in"] = length_to_in(length, dim_unit)
    internal["physical"]["dimensions"]["package"]["width_in"] = length_to_in(width, dim_unit)
    internal["physical"]["dimensions"]["package"]["height_in"] = length_to_in(height, dim_unit)
    internal["physical"]["weight"]["package_lb"] = weight_to_lb(weight, weight_unit)

    print(f"DEBUG fill_bh_packaging internal: {internal["physical"]["dimensions"]["package"]["length_in"]}, {internal["physical"]["dimensions"]["package"]["width_in"]}, {internal["physical"]["dimensions"]["package"]["height_in"]}, {internal["physical"]["weight"]["package_lb"]}")

