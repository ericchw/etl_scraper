"""Shared CDW raw payload helpers."""

from __future__ import annotations

import re


def cdw_payload(raw: dict) -> dict:
    nested = raw.get("scraped_data", {}).get("cdw")
    if isinstance(nested, dict) and nested:
        return nested
    if raw.get("source") == "cdw" or raw.get("specs"):
        return raw
    return {}


def parse_inch(text: str) -> str:
    match = re.search(r"([\d.]+)\s*inch", text, re.I)
    if match:
        return match.group(1)
    return ""


def fill_identity_content(
    internal: dict,
    *,
    raw: dict,
    cdw: dict,
    specs: dict,
    spec_value,
) -> None:
    internal["identity"]["brand"] = spec_value(specs, "Overview", "Brand")
    internal["identity"]["mpn"] = str(raw.get("mpn") or cdw.get("mpn") or "").strip().upper()
    internal["identity"]["product_line"] = spec_value(specs, "Overview", "Product Line")
    internal["identity"]["model"] = spec_value(specs, "Overview", "Model")
    internal["identity"]["product_type"] = spec_value(
        specs, "Product Information", "Product Type"
    )

    internal["content"]["title"] = str(cdw.get("title") or raw.get("title") or "").strip()
    internal["content"]["description"] = str(
        cdw.get("description") or raw.get("description") or ""
    ).strip()
    internal["content"]["features"] = list(cdw.get("features") or raw.get("features") or [])
    images = cdw.get("images") or raw.get("images") or raw.get("scraped_image_urls") or []
    internal["content"]["images"] = list(images)


# def fill_item_dimensions_weight(
#     internal: dict,
#     specs: dict,
#     *,
#     spec_value,
#     length_to_in,
#     weight_to_lb,
# ) -> None:
#     dim_group = "Dimensions & Weight"
#     if not spec_value(specs, dim_group, "Height"):
#         dim_group = "Physical Characteristics"
#
#     h = spec_value(specs, dim_group, "Height") or spec_value(
#         specs, "Dimensions & Weight", "Height"
#     )
#     w = spec_value(specs, dim_group, "Width") or spec_value(
#         specs, "Dimensions & Weight", "Width"
#     )
#     d = spec_value(specs, dim_group, "Depth") or spec_value(
#         specs, "Dimensions & Weight", "Depth"
#     )
#     wt = spec_value(specs, dim_group, "Weight") or spec_value(
#         specs, "Dimensions & Weight", "Weight"
#     )
#
#     internal["physical"]["dimensions"]["item"]["height_in"] = length_to_in(h)
#     internal["physical"]["dimensions"]["item"]["width_in"] = length_to_in(w)
#     internal["physical"]["dimensions"]["item"]["length_in"] = length_to_in(d)
#     internal["physical"]["weight"]["item_lb"] = weight_to_lb(wt)

def _extract_dimension_details(text: str) -> dict:
    result = {}
    try:

        if not text:
            return result

        patterns = {
            "with_stand": r"With stand.*?width:\s*([\d.]+)\s*cm.*?depth:\s*([\d.]+)\s*cm.*?height:\s*([\d.]+)\s*cm.*?weight:\s*([\d.]+)\s*kg",
            "without_stand": r"Without stand.*?width:\s*([\d.]+)\s*cm.*?depth:\s*([\d.]+)\s*cm.*?height:\s*([\d.]+)\s*cm.*?weight:\s*([\d.]+)\s*kg",
        }

        for key, pattern in patterns.items():

            m = re.search(pattern, text, re.I)

            if not m:
                continue

            result[key] = {
                "width": m.group(1),
                "depth": m.group(2),
                "height": m.group(3),
                "weight": m.group(4),
            }
    except Exception as e:
        print(f"_extract_dimension_details error: {e}")
    return result

# def fill_item_dimensions_weight(
#     internal: dict,
#     specs: dict,
#     *,
#     spec_value,
#     length_to_in,
#     weight_to_lb,
# ) -> None:
#     try:
#         dim_group = "Dimensions & Weight"
#
#         if not spec_value(specs, dim_group, "Height"):
#             dim_group = "Physical Characteristics"
#
#         h = spec_value(specs, dim_group, "Height")
#         w = spec_value(specs, dim_group, "Width")
#         d = spec_value(specs, dim_group, "Depth")
#         wt = spec_value(specs, dim_group, "Weight")
#
#         # ----------------------------------
#         # existing item
#         # ----------------------------------
#
#         internal["physical"]["dimensions"]["item"]["height_in"] = length_to_in(h)
#         internal["physical"]["dimensions"]["item"]["width_in"] = length_to_in(w)
#         internal["physical"]["dimensions"]["item"]["length_in"] = length_to_in(d)
#
#         internal["physical"]["weight"]["item_lb"] = weight_to_lb(wt)
#
#         # ----------------------------------
#         # monitor stand details
#         # ----------------------------------
#
#         details = spec_value(
#             specs,
#             "Dimensions & Weight",
#             "Dimensions Details"
#         )
#
#         parsed = _extract_dimension_details(details)
#
#         if not parsed:
#             return
#
#         dims = internal["physical"]["dimensions"]
#         weight = internal["physical"]["weight"]
#
#         if "with_stand" in parsed:
#
#             s = parsed["with_stand"]
#
#             dims["item_with_stand"] = {
#                 "length_in": length_to_in(s["depth"], "cm"),
#                 "width_in": length_to_in(s["width"], "cm"),
#                 "height_in": length_to_in(s["height"], "cm"),
#             }
#
#             weight["item_with_stand_lb"] = weight_to_lb(
#                 s["weight"],
#                 "kg",
#             )
#
#         if "without_stand" in parsed:
#
#             s = parsed["without_stand"]
#
#             dims["item_without_stand"] = {
#                 "length_in": length_to_in(s["depth"], "cm"),
#                 "width_in": length_to_in(s["width"], "cm"),
#                 "height_in": length_to_in(s["height"], "cm"),
#             }
#
#             weight["item_without_stand_lb"] = weight_to_lb(
#                 s["weight"],
#                 "kg",
#             )
#     except Exception as e:
#         print(f"_extract_dimension_details error: {e}")

import re

def fill_item_dimensions_weight(
    internal: dict,
    specs: dict,
    *,
    spec_value,
    length_to_in,
    weight_to_lb,
) -> None:

    physical = internal.setdefault("physical", {})
    dims = physical.setdefault("dimensions", {})
    weight = physical.setdefault("weight", {})

    # ----------------------------
    # helpers
    # ----------------------------
    def first(*vals):
        for v in vals:
            if v not in (None, "", [], {}):
                return v
        return ""

    def parse_mnt_details(text: str):
        """
        extract:
        With stand (highest position) - width: x - depth: y - height: z
        Without stand - ...
        """
        if not text:
            return {}

        result = {
            "with_stand_highest": {},
            "with_stand_lowest": {},
            "without_stand": {},
        }

        blocks = text.split(",")

        for b in blocks:
            b_low = b.lower()

            def extract(key):
                m = re.search(rf"{key}:\s*([\d.]+)", b_low)
                return m.group(1) if m else ""

            if "highest" in b_low:
                result["with_stand_highest"] = {
                    "width": extract("width"),
                    "depth": extract("depth"),
                    "height": extract("height"),
                    "weight": extract("weight"),
                }

            elif "lowest" in b_low:
                result["with_stand_lowest"] = {
                    "width": extract("width"),
                    "depth": extract("depth"),
                    "height": extract("height"),
                    "weight": extract("weight"),
                }

            elif "without stand" in b_low:
                result["without_stand"] = {
                    "width": extract("width"),
                    "depth": extract("depth"),
                    "height": extract("height"),
                    "weight": extract("weight"),
                }

        return result

    # =========================================================
    # 1. ITEM DIMENSIONS (CDW / BH shared base)
    # =========================================================
    h = first(
        spec_value(specs, "Dimensions & Weight", "Height"),
        spec_value(specs, "Physical Characteristics", "Height"),
    )

    w = first(
        spec_value(specs, "Dimensions & Weight", "Width"),
        spec_value(specs, "Physical Characteristics", "Width"),
    )

    d = first(
        spec_value(specs, "Dimensions & Weight", "Depth"),
        spec_value(specs, "Physical Characteristics", "Depth"),
    )

    wt = first(
        spec_value(specs, "Dimensions & Weight", "Weight"),
        spec_value(specs, "Physical Characteristics", "Weight"),
    )

    dims.setdefault("item", {})
    if h: dims["item"]["height_in"] = length_to_in(h)
    if w: dims["item"]["width_in"] = length_to_in(w)
    if d: dims["item"]["length_in"] = length_to_in(d)
    if wt: weight["item_lb"] = weight_to_lb(wt)

    # =========================================================
    # 2. MNT SPECIAL CASE (override if exists)
    # =========================================================
    details = spec_value(specs, "Dimensions & Weight", "Dimensions Details")

    if details:
        parsed = parse_mnt_details(details)

        dims.setdefault("item_with_stand", {})
        dims.setdefault("item_without_stand", {})

        hs = parsed.get("with_stand_highest", {})
        ls = parsed.get("with_stand_lowest", {})
        wo = parsed.get("without_stand", {})


        # highest position
        if hs:
            dims["item_with_stand"].setdefault("highest_position", {})
            if hs.get("width"):
                dims["item_with_stand"]["highest_position"]["width_in"] = length_to_in(hs["width"])
            if hs.get("depth"):
                dims["item_with_stand"]["highest_position"]["length_in"] = length_to_in(hs["depth"])
            if hs.get("height"):
                dims["item_with_stand"]["highest_position"]["height_in"] = length_to_in(hs["height"])
            if hs.get("weight"):
                weight["item_with_stand_lb"] = weight_to_lb(hs["weight"])

        # lowest position
        if ls:
            dims["item_with_stand"].setdefault("lowest_position", {})
            if ls.get("width"):
                dims["item_with_stand"]["lowest_position"]["width_in"] = length_to_in(ls["width"])
            if ls.get("depth"):
                dims["item_with_stand"]["lowest_position"]["length_in"] = length_to_in(ls["depth"])
            if ls.get("height"):
                dims["item_with_stand"]["lowest_position"]["height_in"] = length_to_in(ls["height"])

        # without stand
        if wo:
            if wo.get("width"):
                dims["item_without_stand"]["width_in"] = length_to_in(wo["width"])
            if wo.get("depth"):
                dims["item_without_stand"]["length_in"] = length_to_in(wo["depth"])
            if wo.get("height"):
                dims["item_without_stand"]["height_in"] = length_to_in(wo["height"])
            if wo.get("weight"):
                weight["item_without_stand_lb"] = weight_to_lb(wo["weight"])

    # =========================================================
    # 3. PACKAGE fallback (BH / CDW / etc)
    # =========================================================
    pkg = first(
        spec_value(specs, "Package Dimensions", "Length"),
        spec_value(specs, "Packaging Info", "Length"),
    )

    pkg_w = first(
        spec_value(specs, "Package Dimensions", "Width"),
        spec_value(specs, "Packaging Info", "Width"),
    )

    pkg_h = first(
        spec_value(specs, "Package Dimensions", "Height"),
        spec_value(specs, "Packaging Info", "Height"),
    )

    pkg_wt = first(
        spec_value(specs, "Package Dimensions", "Weight"),
        spec_value(specs, "Packaging Info", "Weight"),
        spec_value(specs, "Shipping", "Weight"),
    )

    dims.setdefault("package", {})
    if pkg: dims["package"]["length_in"] = length_to_in(pkg)
    if pkg_w: dims["package"]["width_in"] = length_to_in(pkg_w)
    if pkg_h: dims["package"]["height_in"] = length_to_in(pkg_h)
    if pkg_wt: weight["package_lb"] = weight_to_lb(pkg_wt)

# def fill_item_dimensions_weight(
#     internal: dict,
#     specs: dict,
#     *,
#     spec_value,
#     length_to_in,
#     weight_to_lb,
# ) -> None:
#
#     # -----------------------------
#     # SAFE INIT HELPERS
#     # -----------------------------
#     def ensure_base():
#         internal.setdefault("dimensions", {})
#         internal.setdefault("weight", {})
#
#     def safe_float(v):
#         try:
#             if v is None:
#                 return None
#             v = str(v).lower().replace("cm", "").replace("kg", "").strip()
#             return float(v)
#         except:
#             return None
#
#     def empty_item():
#         return {"length_in": "", "width_in": "", "height_in": ""}
#
#     def empty_weight():
#         return ""
#
#     ensure_base()
#
#     dim_group = "Dimensions & Weight"
#     if not spec_value(specs, dim_group, "Height"):
#         dim_group = "Physical Characteristics"
#
#     details = spec_value(specs, dim_group, "Dimensions Details")
#
#     # =====================================================
#     # CASE 1: MONITOR (Dimensions Details exists)
#     # =====================================================
#     if details:
#
#         # FULL MONITOR STRUCTURE (WITH STAND / WITHOUT STAND)
#         internal["dimensions"] = {
#             "item_with_stand": empty_item(),
#             "item_without_stand": empty_item(),
#             "package": empty_item()
#         }
#
#         internal["weight"] = {
#             "item_lb": "",
#             "package_lb": ""
#         }
#
#         pattern = (
#             r"(with stand|without stand)\s*-\s*"
#             r"width:\s*([\d.]+)\s*cm\s*-\s*"
#             r"depth:\s*([\d.]+)\s*cm\s*-\s*"
#             r"height:\s*([\d.]+)\s*cm\s*-\s*"
#             r"weight:\s*([\d.]+)\s*kg"
#         )
#
#         parsed = {}
#
#         for m in re.finditer(pattern, details, re.IGNORECASE):
#             label, w, d, h, wt = m.groups()
#             parsed[label.lower().replace(" ", "_")] = {
#                 "width": safe_float(w),
#                 "depth": safe_float(d),
#                 "height": safe_float(h),
#                 "weight": safe_float(wt),
#             }
#
#         # -------------------------
#         # WITH STAND
#         # -------------------------
#         if "with_stand" in parsed:
#             ws = parsed["with_stand"]
#             internal["dimensions"]["item_with_stand"] = {
#                 "length_in": length_to_in(ws["depth"]) if ws["depth"] is not None else "",
#                 "width_in": length_to_in(ws["width"]) if ws["width"] is not None else "",
#                 "height_in": length_to_in(ws["height"]) if ws["height"] is not None else "",
#             }
#             internal["weight"]["item_lb"] = (
#                 weight_to_lb(ws["weight"]) if ws["weight"] is not None else ""
#             )
#
#         # -------------------------
#         # WITHOUT STAND
#         # -------------------------
#         if "without_stand" in parsed:
#             wos = parsed["without_stand"]
#             internal["dimensions"]["item_without_stand"] = {
#                 "length_in": length_to_in(wos["depth"]) if wos["depth"] is not None else "",
#                 "width_in": length_to_in(wos["width"]) if wos["width"] is not None else "",
#                 "height_in": length_to_in(wos["height"]) if wos["height"] is not None else "",
#             }
#             internal["weight"]["item_lb"] = (
#                 weight_to_lb(wos["weight"]) if wos["weight"] is not None else internal["weight"]["item_lb"]
#             )
#
#         return
#
#     # =====================================================
#     # CASE 2: NORMAL PRODUCTS (NO DIMENSIONS DETAILS)
#     # =====================================================
#
#     internal["dimensions"] = {
#         "item": empty_item(),
#         "package": empty_item()
#     }
#
#     internal["weight"] = {
#         "item_lb": "",
#         "package_lb": ""
#     }
#
#     h = safe_float(spec_value(specs, dim_group, "Height"))
#     w = safe_float(spec_value(specs, dim_group, "Width"))
#     d = safe_float(spec_value(specs, dim_group, "Depth"))
#     wt = safe_float(spec_value(specs, dim_group, "Weight"))
#
#     if h is not None:
#         internal["dimensions"]["item"]["height_in"] = length_to_in(h)
#     if w is not None:
#         internal["dimensions"]["item"]["width_in"] = length_to_in(w)
#     if d is not None:
#         internal["dimensions"]["item"]["length_in"] = length_to_in(d)
#
#     if wt is not None:
#         internal["weight"]["item_lb"] = weight_to_lb(wt)

def to_int_number(text: str) -> int | None:
    text = text.strip().lower()

    scale_map = {
        "hundred": 100,
        "thousand": 1_000,
        "million": 1_000_000,
        "billion": 1_000_000_000,
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000,
    }

    # extract number + scale anywhere in the string (ignore trailing words like "colors")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(hundred|thousand|million|billion|k|m|b)?", text)
    if not match:
        return None

    num = float(match.group(1))
    scale = match.group(2)

    if scale:
        num *= scale_map[scale]

    return int(num)

def match_any(text: str, target_str_list: list[str]) -> bool:
    print(text)
    text = text.strip().lower()
    print(text, any(t.lower() in text for t in target_str_list))
    return any(t.lower() in text for t in target_str_list)

def extract_display_type(text: str) -> str | None:
    text = text.strip().upper()
    display_types = ["OLED", "LCD", "LED"]
    for dtype in display_types:
        if dtype in text:
            return dtype
    return ""

if __name__ == "__main__":
    print(to_int_number("16.7 million colors"))

    text = "Height, Pivot (rotation), Swivel, Tilt"
    targets = ["pivot", "swivel"]
    print(match_any(text, targets))

    print(extract_display_type("LED-backlit LCD monitor"))  # "LCD"
    print(extract_display_type("LED-backlit LED monitor"))  # "LED"
    print(extract_display_type("OLED monitor"))  # "OLED"
    print(extract_display_type("Some unknown type"))  # None

    text = "Yes"
    targets = ["yes"]
    print(match_any(text, targets))