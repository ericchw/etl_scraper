"""Named transforms referenced from marketplace YAML field rules."""

from __future__ import annotations

import re
import ast
from datetime import datetime
from typing import Any
import json
from pathlib import Path
from functools import lru_cache
from core.conditions import resolve_condition
from core.brand import resolve_brand

@lru_cache
def load_spec_label() -> dict:
    ROOT = Path(__file__).resolve().parent.parent
    SPEC_LABEL_PATH = ROOT / "configs" / "spec_label.json"

    if not SPEC_LABEL_PATH.exists():
        return {}

    with open(SPEC_LABEL_PATH, encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def only_number(value: Any, **_kwargs) -> str:
    match = re.search(r"\d+(?:\.\d+)?", clean(value))
    return match.group(0) if match else ""

def only_number_1dp(value: Any, **_kwargs) -> str:
    match = re.search(r"\d+(?:\.\d+)?", clean(value))
    return f"{float(match.group(0)):.1f}" if match else ""

def only_number_2dp(value: Any, **_kwargs) -> str:
    match = re.search(r"\d+(?:\.\d+)?", clean(value))
    return f"{float(match.group(0)):.2f}" if match else ""

def only_digits(value: Any, **_kwargs) -> str:
    match = re.search(r"\d+", clean(value))
    return match.group(0) if match else ""


def spec_yes_no(value: Any, **_kwargs) -> str:
    text = clean(value).strip().lower()
    print(f"spec_yes_no: {value}, {text}")

    if not text:
        return ""

    base = text.split("(")[0].strip()

    if base.startswith("yes") or base in {"y", "true", "1"}:
        return "Yes"

    if base.startswith("no") or base in {"n", "false", "0", "none"}:
        return "No"

    # IMPORTANT: don't silently return empty for "Yes (RGB)"
    if "yes" in base:
        return "Yes"
    if "no" in base:
        return "No"

    return ""


def spec_y_n(value: Any, **_kwargs) -> str:
    text = clean(value).lower()
    if text in {"yes", "y", "true", "1"}:
        return "Y"
    if text in {"no", "n", "false", "0", "none"}:
        return "N"
    return ""


def extract_80211(value: Any, **_kwargs) -> str:
    text = clean(value)
    if not text:
        return ""
    match = re.search(r"802\.11[^\s,)]*", text)
    return match.group(0) if match else ""


def extract_bluetooth(value: Any, **_kwargs) -> str:
    text = clean(value)
    if not text:
        return "No"
    match = re.search(r"Bluetooth(?:\s*\d+(?:\.\d+)?)?", text, re.I)
    if not match:
        return "No"
    label = match.group(0)
    if label.lower() == "bluetooth":
        return "Yes"
    return f"Yes - {label}"

def extract_ethernet_speed(value: Any, **_kwargs) -> str:
    text = clean(value)
    if not text:
        return ""

    lowered = text.lower()

    # ---- explicit phrase priority (longest first) ----
    SPEED_MAP = {
        "10 gigabit": 10000,
        "5 gigabit": 5000,
        "2.5 gigabit": 2500,
        "gigabit ethernet": 1000,
        "gigabit": 1000,
        "10mbps": 10,
        "100mbps": 100,
        "2.5g": 2500,
        "5g": 5000,
        "2500mbps": 2500,
        "5000mbps": 5000,
    }

    for key in sorted(SPEED_MAP, key=len, reverse=True):
        if key in lowered:
            return str(SPEED_MAP[key])

    # ---- numeric parsing (Mbps / Gbps / G) ----
    match = re.search(r"(\d+(?:\.\d+)?)\s*(tbps|gbps|mbps|g)?", lowered)
    if match:
        num = float(match.group(1))
        unit = match.group(2)

        if unit in ("gbps", "g"):
            num *= 1000
        elif unit == "tbps":
            num *= 1_000_000

        return str(int(num))

    return ""

def normalize_capacity(text: str, target_unit: str = "GB", show_unit: bool = False, add_space: bool = False,):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|PB)", text, re.I,)

    if not m:
        return ""

    value = float(m.group(1))
    source_unit = m.group(2).upper()
    target_unit = target_unit.upper()

    factors = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
        "PB": 1024**5,
    }

    bytes_value = value * factors[source_unit]
    result = bytes_value / factors[target_unit]

    result = (int(result) if result.is_integer() else round(result, 2))

    if not show_unit:
        return result

    sep = " " if add_space else ""
    return f"{result}{sep}{target_unit}"

"""
normalize_capacity("512GB SSD")
# 512

normalize_capacity("1TB NVMe SSD")
# 1024

normalize_capacity("16GB DDR5")
# 16

normalize_capacity("8GB GDDR6")
# 8

normalize_capacity("32MB Cache")
# 0.03125 (if target GB)

normalize_capacity("1.92TB Enterprise SSD")
# 1966.08
"""

def join_specs(value, *, context, sources=None, **kwargs):
    """Deprecated: use YAML `sources` with `join` instead of this transform."""
    from core.mapping.sources import resolve_sources

    rule = {"sources": sources or [], "join": kwargs.get("join", " ")}
    return resolve_sources(rule, context)

def ssd_capacity_gb(value: Any, *, context: dict, **_kwargs) -> str:
    internal = context.get("internal") or {}
    storage = internal.get("storage") or {}
    storage_type = clean(storage.get("type", "")).upper()
    if storage_type != "SSD":
        return ""
    return only_digits(clean(value))

def hdd_capacity_gb(value: Any, *, context: dict, **_kwargs) -> str:
    internal = context.get("internal") or {}
    storage = internal.get("storage") or {}
    storage_type = clean(storage.get("type", "")).upper()
    if storage_type != "HDD":
        return ""
    return only_digits(clean(value))

def capacity_with_unit(value: Any, **_kwargs) -> str:
    try:
        size = float(clean(value))  # GB
    except (TypeError, ValueError):
        return ""

    units = [
        ("EB", 1_000_000_000),
        ("PB", 1_000_000),
        ("TB", 1_000),
        ("GB", 1),
        ("MB", 0.001),
        ("KB", 0.000001),
        ("B", 0.000000001),
    ]

    for unit, factor in units:
        if size >= factor:
            return f"{int(round(size,0)) / factor:g}{unit}"

    return "0B"

def ssd_capacity_with_unit(value: Any, *, context: dict, **_kwargs,) -> str:
    storage = (context.get("internal") or {}).get("storage") or {}
    if clean(storage.get("type")).upper() != "SSD":
        return ""
    return capacity_with_unit(value)

def hdd_capacity_with_unit(value: Any, *, context: dict, **_kwargs,) -> str:
    storage = (context.get("internal") or {}).get("storage") or {}
    if clean(storage.get("type")).upper() != "HDD":
        return ""
    return capacity_with_unit(value)

def gpu_type(value: Any, *, context: dict, **_kwargs) -> str:
    del value
    internal = context.get("internal") or {}
    integrated_cpu = clean(internal.get("graphics", {}).get("processor", {}).get("model", "")).lower()
    discrete_gpu = clean(internal.get("graphics", {}).get("discrete_graphics_processor", ""))
    is_intel = "intel" in integrated_cpu
    has_discrete = discrete_gpu not in (None, "", [])
    if is_intel and not has_discrete: return "Integrated"
    if is_intel and has_discrete: return "Dedicated"
    return ""

def gpu_type_suffix(value: Any, *, context: dict, **_kwargs) -> str:
    del value
    internal = context.get("internal") or {}
    integrated_cpu = clean(internal.get("graphics", {}).get("processor", {}).get("model", "")).lower()
    discrete_gpu = clean(internal.get("graphics", {}).get("discrete_graphics_processor", ""))
    is_intel = "intel" in integrated_cpu
    has_discrete = discrete_gpu not in (None, "", [])
    if is_intel and not has_discrete: return "Integrated GPU"
    if is_intel and has_discrete: return "Dedicated GPU"
    return ""

# def scraped_image_url(
#     value: Any,
#     *,
#     context: dict,
#     image_index: int = 1,
#     **_kwargs,
# ) -> str:
#     del value
#     images = context.get("images") or []
#     idx = max(1, int(image_index)) - 1
#     if idx >= len(images):
#         return ""
#     return clean(images[idx])

def scraped_image_url(value, *, context, image_index=1, **_kwargs):
    images = context.get("images") or []
    idx = max(1, int(image_index)) - 1

    if idx >= len(images):
        # print(f"image_index={image_index} -> OUT OF RANGE")
        return ""

    result = clean(images[idx])
    # print(f"image_index={image_index} -> {result}")

    return result

def _condition_label(condition: Any) -> str:
    print(type(condition), condition)
    if isinstance(condition, dict):
        return clean(condition.get("label") or condition.get("key") or "")
    if isinstance(condition, str):
        resolved = resolve_condition(condition)
        return clean(resolved.get("label") or condition)
    return ""


def _condition_from_context(context: dict) -> dict:
    condition = context.get("condition")
    if isinstance(condition, dict):
        return condition
    if isinstance(condition, str) and condition:
        return resolve_condition(condition)
    return {}


def bb_title(value: Any, *, context: dict, **_kwargs) -> str:
    print("bb_title", value)
    print("bb_title", context)
    title = clean(context.get("title")).replace(" - ", ", ") or value
    mpn = clean(context.get("mpn") or "")
    if not title and not mpn:
        return ""

    base = f"{title} ({mpn})" if mpn else title
    label = _condition_label(context.get("condition"))
    if label != "Brand New":
        return f"{label} - {base}" #–
    return base


def ne_title(value: Any, *, context: dict, **_kwargs) -> str:
    del value
    title = clean(context.get("title")).replace(" - ", ", ")
    mpn = clean(context.get("mpn"))
    base = f"{title} ({mpn})"
    label = clean(_condition_from_context(context).get("label") or "")
    if label != "Brand New":
        label = label.replace("Open Box", "Open_Box")
        return f"{label} - {base}" #–
    return base


def preserve_multiline(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def format_features_bullets(features: list | None) -> str:
    if not features:
        return ""
    return "\n".join(f"• {item}" for item in features if str(item).strip())


def features_list_from_context(context: dict) -> list[str]:
    internal = context.get("internal") or {}
    content = internal.get("content") or {}
    feats = content.get("features") or context.get("product", {}).get("features") or []
    if isinstance(feats, list):
        return [str(f) for f in feats if str(f).strip()]
    return []


def design_body_from_context(context: dict) -> str:
    internal = context.get("internal") or {}
    content = internal.get("content") or {}
    product = context.get("product") or {}
    return preserve_multiline(
        content.get("description") or product.get("description") or ""
    )

def format_features_bullets(features: list | None) -> str:
    if not features:
        return ""
    return "\n".join(str(item).strip() for item in features if str(item).strip())


# =========================
# NEWEGG (plain text)
# =========================
def export_features(value: Any, *, context: dict, **_kwargs) -> str:
    del value

    features = context.get("features_text") or format_features_bullets(
        features_list_from_context(context)
    )

    label = clean(_condition_from_context(context).get("label") or "")

    if label in (
        "Open Box",
        "Refurbished Excellent",
        "Refurbished Good",
        "Refurbished Fair",
    ):
        prefix = f"{label}: UNUSED, 10/10 condition product w/ full warranty still valid, original accessories ALL are include"
        return f"{prefix}\n{features}" if features else prefix

    return features or ""


# =========================
# BEST BUY (bulleted text)
# =========================
def export_features_bullets(value: Any, *, context: dict, **_kwargs) -> str:
    del value

    features = context.get("features_text") or format_features_bullets(
        features_list_from_context(context)
    )

    label = clean(_condition_from_context(context).get("label") or "")

    lines = []

    if label in (
        "Open Box",
        "Refurbished Excellent",
        "Refurbished Good",
        "Refurbished Fair",
    ):
        prefix = f"{label}: UNUSED, 10/10 condition product w/ full warranty still valid, original accessories ALL are include"
        lines.append(f"• {prefix}")

    if features:
        for line in features.splitlines():
            line = line.strip()
            if line:
                lines.append(f"• {line.lstrip('• ').strip()}")

    return "\n".join(lines)

def export_product_description(
    value: Any,
    *,
    context: dict,
    design_heading: str = "",
    spec_heading: str = "",
    **_kwargs,
) -> str:
    print(f"export_product_description - value: {value}")
    print(f"export_product_description - context: {context}")
    print(f"export_product_description - design_heading: {design_heading}")
    print(f"export_product_description - spec_heading: {spec_heading}")

    del value
    # print("design_heading", design_heading)
    internal = (context.get("product") or {}).get("internal") or {}
    design = internal.get("content", {}).get("description", "")
    specs = {
        k: v
        for k, v in internal.items()
        if k not in {"identity", "content", "images"}
    }

    return build_long_description_text(
        design_text=design,
        specs=specs,
        design_heading=design_heading,
        spec_heading=spec_heading,
    )

def ne_long_description(
    value: Any,
    *,
    context: dict,
    design_heading: str = "",
    spec_heading: str = "",
    **_kwargs,
) -> str:
    description = export_product_description(
        value,
        context=context,
        design_heading=design_heading,
        spec_heading=spec_heading,
        **_kwargs,
    )

    return description.replace("　", "  ")

def bb_long_description(
    value: Any,
    *,
    context: dict,
    design_heading: str = "",
    spec_heading: str = "",
    **_kwargs,
) -> str:
    return export_product_description(
        value,
        context=context,
        design_heading=design_heading,
        spec_heading=spec_heading,
        **_kwargs,
    )

# def load_spec_label() -> dict:
#     ROOT = Path(__file__).resolve().parent.parent
#     SPEC_LABEL_PATH = ROOT / "configs" / "spec_label.json"
#
#     if not SPEC_LABEL_PATH.exists():
#         return {}
#     with open(SPEC_LABEL_PATH, encoding="utf-8") as f:
#         data = json.load(f)
#     return data if isinstance(data, dict) else {}

def format_label(key: str) -> str:
    key = key.strip()

    labels = load_spec_label()

    if key in labels:
        return labels[key]

    return key.replace("_", " ").title()


def build_specs_text(specs: dict | None) -> str:
    if not specs:
        return ""

    lines: list[str] = []

    def render(value, indent: int, label: str | None = None):
        pad = "　" * indent

        if isinstance(value, dict):
            if label:
                lines.append(f"{pad}{label}")

            for k, v in value.items():
                if v in (None, "", [], {}):
                    continue

                render(v, indent + 1, format_label(k))

        elif isinstance(value, list):
            if label:
                lines.append(f"{pad}{label}: {', '.join(map(str, value))}")

        else:
            if label:
                lines.append(f"{pad}{label}: {value}")

    # # ✅ ROOT HEADER (level 0)
    # lines.append("Specifications:")

    for section, data in specs.items():
        if not isinstance(data, dict):
            continue

        # ✅ SECTION MUST ALWAYS BE LEVEL 1
        section_label = format_label(section)
        lines.append(f"　{section_label}")

        render(data, 2)

    return "\n".join(lines).strip()

def build_long_description_text(
    *,
    design_text: str,
    specs: dict | None,
    design_heading: str = "",
    spec_heading: str = "",
) -> str:
    parts: list[str] = []
    body = preserve_multiline(design_text)
    if body:
        heading = (design_heading or "").strip()
        if heading and not body.lstrip().startswith(heading):
            parts.append(f"{heading}\n{body}")
        else:
            parts.append(body)
    specs_block = build_specs_text(specs)
    if specs_block:
        parts.append(f"{spec_heading}\n　{specs_block}")
    return "\n\n".join(parts)


def bb_product_condition(value: Any, *, context: dict, **_kwargs) -> str:
    del value
    label = clean(_condition_from_context(context).get("label") or "")
    return label or "Brand New"


def ne_product_condition(value: Any, *, context: dict, **_kwargs) -> str:
    del value
    label = clean(_condition_from_context(context).get("label") or "")
    if label in ("Open Box", "Refurbished Excellent", "Refurbished Good", "Refurbished Fair"):
        return "Refurbished"
    return "New"

def warranty_url_by_brand(value: Any, *, context: dict, **_kwargs) -> str:
    del value

    WARRANTY_URLS = {
        "dell": "https://www.dell.com/support/contractservices/en-ca",
        "samsung": "https://www.samsung.com/ca/support/warranty/",
    }

    brand = clean(context["get_spec"]("Overview", "Brand")).lower()
    return WARRANTY_URLS.get(brand, "")


def start_of_day_pst(value: Any, **_kwargs) -> str:
    text = clean(value)
    if not text:
        return ""
    dt = datetime.strptime(text, "%Y-%m-%d")
    return dt.strftime("%Y-%m-%dT00:00:00.000-07:00")


def end_of_day_pst(value: Any, **_kwargs) -> str:
    text = clean(value)
    if not text:
        return ""
    dt = datetime.strptime(text, "%Y-%m-%d")
    return dt.strftime("%Y-%m-%dT23:59:59.999-07:00")

def length_in_to_cm(value: Any, **_kwargs) -> str:
    if not value:
        return ""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{n * 2.54:.2f}"

def weight_lb_to_kg(value: Any, **_kwargs) -> str:
    if not value:
        return ""

    try:
        n = float(value)
    except (TypeError, ValueError):
        return ""

    return f"{n / 2.20462:.3f}"

def weight_lb_to_g(value: Any, **_kwargs) -> str:
    if not value:
        return ""

    try:
        n = float(value)
    except (TypeError, ValueError):
        return ""

    return f"{n * 453.59237:.3f}"

def contains_keywords(obj, keywords) -> bool:
    if isinstance(obj, dict):
        return any(contains_keywords(v, keywords) for v in obj.values())

    if isinstance(obj, list):
        return any(contains_keywords(v, keywords) for v in obj)

    text = str(obj).lower()
    normalized = text.replace("-", "").replace(" ", "")

    return any(
        keyword.lower().replace("-", "").replace(" ", "") in normalized
        for keyword in keywords
    )

def check_anti_glare(value, *, context, **kwargs) -> str:
    del value
    keywords = ("anti glare", "anti-glare", "antiglare")
    return ("Yes" if contains_keywords(context, keywords)
            else "No")

def check_stylus(value, *, context, **kwargs) -> str:
    del value
    keywords = ("stylus", "pen", "inking",)
    return ("Yes" if contains_keywords(context, keywords)
        else "No")

def check_cellular(value, *, context, **kwargs) -> str:
    del value
    keywords = ("4g", "5g", "cellular", "nanosim")
    print('check_cellular:', context)
    return ("Yes" if contains_keywords(context, keywords) else "")

def check_copilotpc(value, *, context, **kwargs) -> str:
    del value
    keywords = ("copilot")
    return ("Yes" if contains_keywords(context, keywords)
        else "No")

def check_hdcp(value, *, context, **kwargs) -> str:
    del value
    keywords = ("hdcp")
    return ("Yes" if contains_keywords(context, keywords)
        else "No")

def bb_check_wifi_standard(value, *, context=None, sources=None, **kwargs) -> str:
    text = clean(value)

    if not text:
        return ""

    # Extract Wi-Fi generation text, e.g. "(Wi-Fi 6E)"
    wifi_gen = ""
    m = re.search(r"(\(Wi-?Fi[^)]*\))", text, re.IGNORECASE)
    if m:
        wifi_gen = f" {m.group(1)}"

    # Remove everything from first "(" onward
    base = text.split("(")[0].strip()

    # Get last standard after "/"
    last = base.split("/")[-1].strip()

    if not last:
        return ""

    return f"802.11{last}{wifi_gen}"

# def ne_check_wifi_standard(value, *, context=None, sources=None, **kwargs) -> str:
#     text = clean(value)
#
#     if not text:
#         return ""
#
#     # Extract Wi-Fi generation text, e.g. "(Wi-Fi 6E)"
#     m = re.search(r"(\(Wi-?Fi[^)]*\))", text, re.IGNORECASE)
#
#     # Remove everything from first "(" onward
#     base = text.split("(")[0].strip()
#
#     # Get last standard after "/"
#     last = base.split("/")[-1].strip()
#
#     if not last:
#         return ""
#
#     return f"802.11{last} Wireless LAN"

def ne_check_wifi_standard(value, *, context=None, sources=None, **kwargs) -> str:
    text = clean(value)

    if not text:
        return ""

    # Handle "IEEE 802.11be"
    m = re.search(r"802\.11([a-z0-9]+)", text, re.IGNORECASE)
    if m:
        return f"802.11{m.group(1)} Wireless LAN"

    # Existing logic for formats like "a/b/g/n/ac/ax/be"
    m = re.search(r"(\(Wi-?Fi[^)]*\))", text, re.IGNORECASE)

    base = text.split("(")[0].strip()
    last = base.split("/")[-1].strip()

    if not last:
        return ""

    return f"802.11{last} Wireless LAN"

def ne_check_wifi_generation(value, *, context=None, sources=None, **kwargs) -> str:
    text = clean(value)
    if not text:
        return ""

    t = text.upper()

    # # Wi-Fi 6E special case
    # if "WI-FI 6E" in t:
    #     return "802.11Wi-Fi 6E Wireless LAN"

    # extract Wi-Fi number (Wi-Fi 7, Wi-Fi 8, Wi-Fi 5, etc.)
    m = re.search(r"WI[- ]?FI\s*([0-9]+)", t)
    if not m:
        return ""

    num = int(m.group(1))

    # legacy grouping
    if num <= 4:
        gen = "Wi-Fi 4 and earlier generation"
    else:
        gen = f"Wi-Fi {num}"

    return f"{gen}"

def ne_check_ethernet_speed(value, *, context=None, sources=None, **kwargs) -> str:
    text = clean(value)

    speed_map = {
        "100": "10/100Mbps",
        "1000": "10/100/1000Mbps",
        "2500": "2.5 Gbps",
    }

    return speed_map.get(text, "")

def ne_check_item_weight_scale(value, *, context=None, sources=None, **kwargs) -> str:
    text = clean(value)
    if not text:
        return ""

    try:
        weight = round(float(text), 2)
    except (ValueError, TypeError):
        return ""

    if weight < 2:
        return "<2 lbs"
    elif weight < 3:
        return "2 - 2.9 lbs."
    elif weight < 4:
        return "3 - 3.9 lbs."
    elif weight < 5:
        return "4 - 4.9 lbs."
    elif weight < 6:
        return "5 - 5.9 lbs."
    elif weight < 7:
        return "6 - 6.9 lbs."
    elif weight < 8:
        return "7 - 7.9 lbs."
    elif weight < 9:
        return "8 - 8.9 lbs."
    elif weight < 10:
        return "9 - 9.9 lbs."
    else:
        return ">10 lbs"

def ne_check_touchscreen(value: Any, **_kwargs) -> str:
    text = clean(value).lower()
    if text in {"yes", "y", "true"}:
        return "Touch Screen"
    if text in {"no", "n", "false", "0", "none"}:
        return "Non-Touch Screen"
    return ""

def ne_check_backlight_keyboard(value: Any, **_kwargs) -> str:
    text = clean(value).lower()
    if "yes" in text:
        return "Backlit"
    if text in {"no", "n", "false", "0", "none"}:
        return "Non-backlit"
    return ""

def get_brand_label(value: Any, *, context, **kwargs) -> str:
    if value:
        value = resolve_brand(value).get('label') or ''
        # print("get_brand value:", value)
    return value

def ne_check_screensize(value: Any, **_kwargs) -> str:
    match = re.search(r"\d+(?:\.\d+)?", clean(value))
    return f'{float(match.group(0)):.1f}"' if match else ""

def bb_extract_display_type(value: Any, **_kwargs) -> str | None:
    text = value.strip().upper()
    display_types = ["OLED", "LCD", "LED"]
    for dtype in display_types:
        if dtype in text:
            return dtype
    return ""

def ne_monitor_convenience_stand_adjustments(value: Any, *, context: dict, **_kwargs) -> str:
    del value

    _ALLOWED = {
        frozenset(): "No",
        frozenset({"height"}): "Height",
        frozenset({"pivot"}): "Pivot",
        frozenset({"tilt"}): "Tilt",
        frozenset({"swivel"}): "Swivel",
        frozenset({"height", "pivot"}): "Height & Pivot",
        frozenset({"height", "tilt"}): "Height & Tilt",
        frozenset({"height", "swivel"}): "Height & Swivel",
        frozenset({"pivot", "tilt"}): "Pivot & Tilt",
        frozenset({"pivot", "swivel"}): "Pivot & Swivel",
        frozenset({"swivel", "tilt"}): "Swivel & Tilt",
        frozenset({"pivot", "swivel", "tilt"}): "Pivot, Swivel & Tilt",
        frozenset({"height", "pivot", "tilt"}): "Height, Pivot, Tilt",
        frozenset({"height", "pivot", "swivel"}): "Height, Pivot, Swivel",
        frozenset({"height", "swivel", "tilt"}): "Height, Swivel, Tilt",
        frozenset({"height", "pivot", "swivel", "tilt"}): "Height, Pivot, Swivel, Tilt",
    }

    internal = context.get("internal") or {}
    adjustment = internal.get("display", {}).get("adjustment", {}) or {}

    features = {
        name
        for name in ("height", "pivot", "swivel", "tilt")
        if adjustment.get(name)
    }

    return _ALLOWED.get(frozenset(features), "")

def ne_curved_surface_screen(value: Any, *, context: dict, **_kwargs) -> str:
    del value
    internal = context.get("internal") or {}
    curve = clean(internal.get("display", {}).get("curve_screen", "")).strip().lower()
    return "Curved" if curve in {"true", "yes"} else "Flat Panel"

def bb_cooler_led_rgb(value: Any, **_kwargs) -> str:
    text = clean(value).lower()
    if not text:
        return ""

    if "rgb" in text:
        return "RGB"
    elif "led" in text:
        return "LED"

    return ""

def bb_cooler_heatsink_material(value: Any, **_kwargs) -> str:
    text = clean(value).lower()
    if not text:
        return ""
    if "copper" in text:
        return "Cooper"
    elif "aluminum" in text:
        return "Aluminum"
    return "Other"

# def bb_cpu_socket_type(value: Any, **_kwargs) -> str:
#     # Convert to dict if necessary
#     if isinstance(value, str):
#         try:
#             value = json.loads(value)  # JSON string
#         except json.JSONDecodeError:
#             try:
#                 value = ast.literal_eval(value)  # Python dict string
#             except (ValueError, SyntaxError):
#                 value = {}
#
#     elif value is None:
#         value = {}
#
#     elif not isinstance(value, dict):
#         value = {}
#
#     result = []
#
#     for socket in value.get("amd", []):
#         result.append(f"AMD {socket}")
#
#     for socket in value.get("intel", []):
#         if socket.upper().startswith("LGA") and not socket.upper().startswith("LGA "):
#             socket = f"LGA {socket[3:]}"
#         result.append(f"Intel {socket}")
#
#     for socket in value.get("pi_nnpi", []):
#         result.append(f"PI/NNPI {socket}")
#
#     return " ".join(result)

def bb_cpu_socket_type(value: Any, **_kwargs) -> str:
    # Convert to dict if necessary
    if isinstance(value, str):
        try:
            value = json.loads(value)  # JSON string
        except json.JSONDecodeError:
            try:
                value = ast.literal_eval(value)  # Python dict string
            except (ValueError, SyntaxError):
                value = {}

    elif value is None:
        value = {}

    elif not isinstance(value, dict):
        value = {}

    result = []

    # Get Intel sockets
    intel = value.get("intel", [])

    if isinstance(intel, list):
        for socket in intel:
            socket = str(socket).strip()

            # Add LGA prefix if it doesn't already have one
            if socket and not socket.upper().startswith("LGA"):
                socket = f"Intel LGA{socket}"

            if socket:
                result.append(socket)

    # Get AMD sockets
    amd = value.get("amd", [])

    if isinstance(amd, list):
        for socket in amd:
            socket = str(socket).strip()

            if socket:
                result.append(socket)

    # Get Pi / NNPI sockets
    pi_nnpi = value.get("pi_nnpi", [])

    if isinstance(pi_nnpi, list):
        for socket in pi_nnpi:
            socket = str(socket).strip()

            if socket:
                result.append(socket)

    return ";".join(result)


def bb_cooler_compatibility(value: Any, **_kwargs) -> str:
    # Convert to dict if necessary
    if isinstance(value, str):
        try:
            value = json.loads(value)  # JSON string
        except json.JSONDecodeError:
            try:
                value = ast.literal_eval(value)  # Python dict string
            except (ValueError, SyntaxError):
                value = {}

    elif value is None:
        value = {}

    elif not isinstance(value, dict):
        value = {}

    result = []

    # Get Intel sockets
    intel = value.get("intel", [])

    if isinstance(intel, list):
        for socket in intel:
            socket = str(socket).strip()

            # Add LGA prefix if it doesn't already have one
            if socket and not socket.upper().startswith("LGA"):
                socket = f"Intel LGA{socket}"

            if socket:
                result.append(socket)

    # Get AMD sockets
    amd = value.get("amd", [])

    if isinstance(amd, list):
        for socket in amd:
            socket = str(socket).strip()

            if socket:
                result.append(socket)

    # Get Pi / NNPI sockets
    pi_nnpi = value.get("pi_nnpi", [])

    if isinstance(pi_nnpi, list):
        for socket in pi_nnpi:
            socket = str(socket).strip()

            if socket:
                result.append(socket)

    return ";".join(result)


# def bb_max_rpm(value: Any, **_kwargs) -> str:
#     text = clean(value)
#     if not text:
#         return ""
#     numbers = re.findall(r"\d+", text)
#     return numbers[-1] if numbers else ""
#
# def bb_min_rpm(value: Any, **_kwargs) -> str:
#     text = clean(value)
#     if not text:
#         return ""
#
#     numbers = re.findall(r"\d+", text)
#     return numbers[0] if numbers else ""

def bb_PCCoolingType(value: Any, **_kwargs) -> str:
    print("bb_PCCoolingType value:", value )
    if not value:
        return ""

    # if "Case Fan" in value:
    #     return "PC Case Fan"
    # elif "Radiator Fan" in value:
    #     return "Radiator Fan"
    if "Fan" in value:
        return "Case/Radiator Fan"
    elif "Remote/Controller" in value:
        return "Remote/Controller"
    elif "Heatsink" in value:
        return "Heatsink only"
    elif "CPU AIO Cooler" in value:
        return "All-in-One Liquid CPU Cooler"
    elif "Thermal Paste" in value:
        return "Thermal Paste"
    elif "CPU Air Cooler" in value:
        return "CPU Air Cooler"
    return "Other"


TRANSFORMS = {
    "clean": clean,
    "only_number": only_number,
    "only_number_1dp": only_number_1dp,
    "only_number_2dp": only_number_2dp,
    "only_digits": only_digits,
    "spec_yes_no": spec_yes_no,
    "spec_y_n": spec_y_n,
    "extract_80211": extract_80211,
    "extract_bluetooth": extract_bluetooth,
    "join_specs": join_specs,
    "ssd_capacity_gb": ssd_capacity_gb,
    "hdd_capacity_gb": hdd_capacity_gb,
    "ssd_capacity_with_unit": ssd_capacity_with_unit,
    "hdd_capacity_with_unit": hdd_capacity_with_unit,
    "gpu_type": gpu_type,
    "gpu_type_suffix": gpu_type_suffix,
    "scraped_image_url": scraped_image_url,
    "bb_title": bb_title,
    "ne_title": ne_title,
    "export_features": export_features,
    "export_features_bullets": export_features_bullets,
    "export_product_description": export_product_description,
    "ne_long_description": ne_long_description,
    "bb_long_description": bb_long_description,
    "bb_product_condition": bb_product_condition,
    "ne_product_condition": ne_product_condition,
    "warranty_url_by_brand": warranty_url_by_brand,
    "start_of_day_pst": start_of_day_pst,
    "end_of_day_pst": end_of_day_pst,
    "length_in_to_cm": length_in_to_cm,
    "weight_lb_to_kg": weight_lb_to_kg,
    "weight_lb_to_g":weight_lb_to_g,
    "check_anti_glare": check_anti_glare,
    "check_stylus": check_stylus,
    "check_cellular": check_cellular,
    "check_copilotpc": check_copilotpc,
    "check_hdcp": check_hdcp,
    "bb_check_wifi_standard": bb_check_wifi_standard,
    "ne_check_wifi_standard": ne_check_wifi_standard,
    "ne_check_wifi_generation": ne_check_wifi_generation,
    "ne_check_ethernet_speed": ne_check_ethernet_speed,
    "ne_check_item_weight_scale": ne_check_item_weight_scale,
    "ne_check_touchscreen": ne_check_touchscreen,
    "ne_check_backlight_keyboard": ne_check_backlight_keyboard,
    "get_brand_label": get_brand_label,
    "ne_check_screensize": ne_check_screensize,
    "bb_extract_display_type": bb_extract_display_type,
    "ne_monitor_convenience_stand_adjustments": ne_monitor_convenience_stand_adjustments,
    "ne_curved_surface_screen": ne_curved_surface_screen,
    "bb_cooler_led_rgb": bb_cooler_led_rgb,
    "bb_cooler_heatsink_material": bb_cooler_heatsink_material,
    "bb_cpu_socket_type": bb_cpu_socket_type,
    "bb_cooler_compatibility": bb_cooler_compatibility,
    # "bb_max_rpm": bb_max_rpm,
    # "bb_min_rpm": bb_min_rpm,
    "bb_PCCoolingType": bb_PCCoolingType,
    "passthrough": clean,
}

if __name__ == "__main__":
    # print(_condition_label("open_box"))
    # print(ne_check_wifi_generation("Intel Wi-Fi 6E AX 211"))

    # data = {
    #     "internal": {
    #         "images": [
    #             "http://webobjects2.cdw.com/is/image/CDW/7840842",
    #             "http://webobjects2.cdw.com/is/image/CDW/7840842a",
    #         ]
    #     }
    # }
    #
    # context = {"images": data["internal"]["images"]}
    #
    # print(scraped_image_url(None, context=context, image_index=1))


    # data = {
    #     "internal": {
    #         "network":{
    #             "wifi": "IEEE 802.11be"
    #         }
    #     }
    # }
    # context = {"network": data["internal"]["network"]["wifi"]}
    #
    # print(ne_check_wifi_standard("IEEE 802.11be"))

    # print(spec_yes_no("No"))

    context = {
        "title": 'LG UltraGear 27G411A-B 27" Class Gaming LCD Monitor',
        "mpn": "27G411A-B",
        "condition": {"label": "Open Box"},
    }

    print(bb_title(None, context=context))



    pass