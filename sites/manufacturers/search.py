"""Resolve manufacturer product URL — site search, redirect detection, Google fallback."""

from __future__ import annotations

from typing import Callable
from urllib.parse import urlparse


def _search_markers(search_url: str) -> list[str]:
    """Heuristic markers that indicate we are still on a search/listing page."""
    lower = (search_url or "").lower()
    markers = []
    for token in ("/search", "search-results", "search?", "?keys=", "?text=", "searchvalue="):
        if token in lower:
            markers.append(token)
    parsed = urlparse(search_url)
    path = (parsed.path or "").lower()
    if "/search/" in path:
        markers.append("/search/")
    return markers or ["/search"]


def _is_search_page(current_url: str, search_url: str) -> bool:
    current = (current_url or "").lower()
    markers = _search_markers(search_url)
    return any(m in current for m in markers)


def _find_product_in_search(page, mpn: str, brand_key: str) -> str | None:
    """Brand-specific search result parsing when still on a listing page."""
    mpn_key = mpn.strip().upper()
    if brand_key == "msi":
        for link in page.query_selector_all("a[href*='/product/']"):
            href = link.get_attribute("href") or ""
            text = (link.inner_text() or "").upper()
            if mpn_key in text or mpn_key in href.upper():
                if href.startswith("/"):
                    href = f"https://ca.msi.com{href}"
                return href
    return None


def resolve_manufacturer_product_url(
    page,
    mpn: str,
    cfg: dict,
    *,
    brand_key: str,
    log: Callable[[str], None] = print,
    wait_for_captcha: Callable[[], None] | None = None,
) -> str | None:
    """
    1. Try ``search_url`` — detect redirect to PDP vs search listing.
    2. If still on search page, parse results for MPN match.
    3. Fall back to Google when ``google_search`` is true.
    """
    url_template = (cfg.get("search_url") or "").strip()
    google_search = bool(cfg.get("google_search"))
    google_cite = (cfg.get("google_cite") or "").strip()
    expect_redirect = bool(cfg.get("redirect"))

    product_url: str | None = None

    if url_template:
        search_url = url_template.format(mpn=mpn)
        if not search_url.startswith("http"):
            search_url = f"https://{search_url.lstrip('/')}"
        log(f"Manufacturer search -> {search_url}")
        page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        current = page.url
        if not _is_search_page(current, search_url):
            log(f"Manufacturer REDIRECT PRODUCT -> {current}")
            return current

        if expect_redirect:
            log("Manufacturer: expected redirect but still on search page")
            if not google_search:
                return None
        else:
            log("Manufacturer: still on search page — parsing results")
            product_url = _find_product_in_search(page, mpn, brand_key)
            if product_url:
                log(f"Manufacturer search match -> {product_url}")
                return product_url
            if not google_search:
                log(f"Manufacturer: no search match for {mpn}")
                return None

    if google_search and google_cite:
        from sites.google.search import google_search_product_url

        product_url = google_search_product_url(
            page,
            mpn,
            google_cite=google_cite,
            log=log,
            wait_for_captcha=wait_for_captcha,
        )
        return product_url

    if not url_template:
        log(f"Manufacturer: no search_url and google_search disabled for {brand_key!r}")
    return None
