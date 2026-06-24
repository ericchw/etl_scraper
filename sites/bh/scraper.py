"""B&H Photo scraper — search mini product page, then PDP."""

from __future__ import annotations

import re
from typing import Callable

from sites.bh.extractors import (
    BH_GET_DESIGN_JS,
    BH_GET_FEATURES_JS,
    BH_GET_IMAGES_JS,
    BH_GET_PACKAGING_JS,
    BH_GET_SPECS_JS,
)


def _parse_specs_text(text: str) -> dict:
    specs: dict = {}
    current_group = "General"
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Specifications"):
            continue
        if line.startswith("　　") and ":" in stripped:
            key, _, val = stripped.partition(":")
            block = specs.setdefault(current_group, {})
            block[key.strip()] = val.strip()
        elif line.startswith("　") and not line.startswith("　　"):
            current_group = stripped
            specs.setdefault(current_group, {})
    return specs


def _parse_box_dimensions(text: str) -> tuple[str, str, str]:
    """Parse e.g. 17.4 x 12.4 x 3.2\" into length, width, height."""
    match = re.search(
        r"([\d.]+)\s*[x×]\s*([\d.]+)\s*[x×]\s*([\d.]+)",
        text or "",
        re.I,
    )
    if not match:
        return "", "", ""
    return match.group(1), match.group(2), match.group(3)


def _mfr_from_sku_info(text: str) -> str:
    match = re.search(r"MFR\s*#\s*([A-Za-z0-9\-]+)", text or "", re.I)
    return match.group(1).strip().upper() if match else ""


def _is_replacement_for_url(url: str) -> bool:
    return "/c/replacement_for/" in (url or "").lower()


def ensure_bh_product_page(page, *, log: Callable[[str], None]) -> bool:
    """
    After navigating from search, B&H may land on /c/replacement_for/…
    Click discontinuedItemNameLink to reach the real PDP; otherwise stay put.
    """
    if not _is_replacement_for_url(page.url):
        log(f"B&H PDP → {page.url}")
        return True

    log(f"B&H: replacement_for redirect → {page.url}")
    el = page.query_selector('[data-selenium="discontinuedItemNameLink"]')
    if not el:
        log("B&H: discontinuedItemNameLink not found")
        return False

    anchor = el.query_selector("a") or page.query_selector(
        'a[data-selenium="discontinuedItemNameLink"]'
    )
    (anchor or el).click()
    page.wait_for_load_state("domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)

    if _is_replacement_for_url(page.url):
        log("B&H: still on replacement_for after click")
        return False

    log(f"B&H PDP (replacement) → {page.url}")
    return True


def open_bh_product_from_search(page, mpn: str, *, log: Callable[[str], None]) -> bool:
    """Stay on search URL; open PDP via mini product page link when MFR matches."""
    mpn_key = mpn.strip().upper()
    try:
        page.wait_for_selector(
            '[data-selenium="listingProductDetailSection"]',
            timeout=60000,
        )
    except Exception:
        log("B&H: listingProductDetailSection not found")
        return False

    page.wait_for_timeout(1500)
    mini_pages = page.query_selector_all('[data-selenium="miniProductPage"]')
    log(f"B&H: {len(mini_pages)} mini product page(s)")

    for mini in mini_pages:
        sku_el = mini.query_selector('[data-selenium="miniProductPageProductSkuInfo"]')
        if not sku_el:
            continue
        sku_text = sku_el.inner_text()
        mfr = _mfr_from_sku_info(sku_text)
        if mfr != mpn_key:
            continue

        log(f"B&H: MFR match {mfr} in {sku_text[:80]!r}…")
        desc = mini.query_selector('[data-selenium="miniProductPageDescription"]')
        link = None
        if desc:
            link = desc.query_selector('a[data-selenium="miniProductPageProductNameLink"]')
        if not link:
            link = mini.query_selector('a[data-selenium="miniProductPageProductNameLink"]')
        if not link:
            log("B&H: product name link not found")
            continue

        link.click()
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        return ensure_bh_product_page(page, log=log)

    log(f"B&H: no mini page with MFR # {mpn_key}")
    return False


def scrape_bh_product(page, mpn: str, *, log: Callable[[str], None] = print) -> dict | None:
    from core.scraper_registry import load_scraper_config

    cfg = load_scraper_config("bh")
    url = (cfg.get("search_url") or "https://www.bhphotovideo.com/c/search?q={mpn}").format(
        mpn=mpn
    )
    log(f"B&H SEARCH → {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    url_lower = page.url.lower()
    if "/c/product/" in url_lower:
        log("B&H: already on product page")
    elif _is_replacement_for_url(page.url):
        if not ensure_bh_product_page(page, log=log):
            return None
    elif not open_bh_product_from_search(page, mpn, log=log):
        return None

    try:
        page.wait_for_selector('[data-selenium="specsItemGroupTable"]', timeout=30000)
    except Exception:
        log("B&H: specs table not found (continuing)")

    page.wait_for_timeout(1500)

    images = page.evaluate(BH_GET_IMAGES_JS) or []
    raw_features = page.evaluate(BH_GET_FEATURES_JS) or []
    description = str(page.evaluate(BH_GET_DESIGN_JS) or "")
    specs_text = page.evaluate(BH_GET_SPECS_JS) or ""

    title = ""
    el = page.query_selector("h1")
    if el:
        title = el.inner_text().strip()

    features: list[str] = []
    if isinstance(raw_features, list):
        features = [str(f).strip() for f in raw_features if str(f).strip()]
    elif isinstance(raw_features, str) and raw_features.strip():
        features = [line.strip() for line in raw_features.splitlines() if line.strip()]

    if features:
        log(f"B&H: {len(features)} feature(s)")
    if description.strip():
        log(f"B&H: description {len(description)} chars")

    specs = _parse_specs_text(specs_text) if specs_text else {}
    packaging = page.evaluate(BH_GET_PACKAGING_JS) or {}
    if packaging:
        log(f"B&H: Packaging Info → {packaging}")
        specs["Packaging Info"] = packaging
    _extract_packaging_into_specs(specs)

    return {
        "source": "bh",
        "mpn": mpn.upper(),
        "title": title,
        "description": description,
        "features": features,
        "images": images,
        "specs": specs,
        "specs_text": specs_text,
        "dim_unit": "in",
        "weight_unit": "lb",
    }


def _extract_packaging_into_specs(specs: dict) -> None:
    """Normalize Packaging Info into Package Dimensions group."""
    pkg = specs.setdefault("Package Dimensions", {})
    packaging = specs.get("Packaging Info") or {}
    if isinstance(packaging, dict):
        for key, val in packaging.items():
            kl = key.lower()
            if "package weight" in kl or kl == "weight":
                pkg.setdefault("Weight", val)
            elif "box dimension" in kl or "package dimension" in kl:
                length, width, height = _parse_box_dimensions(str(val))
                if length:
                    pkg.setdefault("Length", length)
                if width:
                    pkg.setdefault("Width", width)
                if height:
                    pkg.setdefault("Height", height)

    packaging_keys = (
        "length",
        "width",
        "height",
        "depth",
        "weight",
        "shipping weight",
        "package weight",
        "package dimensions",
        "box dimension",
    )
    for group, entries in list(specs.items()):
        if not isinstance(entries, dict):
            continue
        gl = group.lower()
        if "packaging" not in gl and "shipping" not in gl:
            continue
        for key, val in entries.items():
            kl = key.lower()
            if "box dimension" in kl or ("dimension" in kl and "x" in str(val).lower()):
                length, width, height = _parse_box_dimensions(str(val))
                if length:
                    pkg.setdefault("Length", length)
                if width:
                    pkg.setdefault("Width", width)
                if height:
                    pkg.setdefault("Height", height)
                continue
            if any(p in kl for p in packaging_keys):
                if "weight" in kl:
                    pkg.setdefault("Weight", val)
                elif "length" in kl:
                    pkg.setdefault("Length", val)
                elif "width" in kl:
                    pkg.setdefault("Width", val)
                elif "height" in kl or "depth" in kl:
                    pkg.setdefault("Height", val)
