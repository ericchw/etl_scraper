"""Google search helper — find manufacturer product page by MPN + cite domain."""

from __future__ import annotations

from typing import Callable
from urllib.parse import quote_plus, urlparse


def _normalize_cite(text: str) -> str:
    """Normalize Google cite text for comparison with google_cite config."""
    raw = (text or "").strip().lower()
    raw = raw.replace(" › ", "/").replace(" ›", "/").replace("›", "/")
    raw = raw.split("\n")[0].strip()
    if not raw.startswith("http"):
        raw = f"https://{raw.lstrip('/')}"
    parsed = urlparse(raw)
    host = (parsed.netloc or parsed.path.split("/")[0]).lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _cite_matches(result_cite: str, expected_cite: str) -> bool:
    if not expected_cite:
        return False
    result_host = _normalize_cite(result_cite)
    expected_host = _normalize_cite(expected_cite)
    return result_host == expected_host or result_host.endswith(f".{expected_host}")


def _is_google_blocked(page) -> bool:
    url = (page.url or "").lower()
    if "/sorry/" in url or "unusual traffic" in (page.title() or "").lower():
        return True
    body = page.locator("body").inner_text(timeout=2000)
    return "unusual traffic" in body.lower()


def _iter_google_results(page):
    """Yield (cite_text, href) for each organic result block."""
    primary = page.locator("#center_col #rso > div > div[data-rpos]")
    count = primary.count()
    for i in range(count):
        block = primary.nth(i)
        if block.locator("div[data-snhf]").count() == 0:
            continue
        cite_el = block.locator('div[data-snhf="0"] cite').first
        if cite_el.count() == 0:
            cite_el = block.locator("cite").first
        link = block.locator('div[data-snhf="0"] span a').first
        if link.count() == 0:
            link = block.locator("a[href^='http']").first
        if cite_el.count() == 0 or link.count() == 0:
            continue
        cite_text = cite_el.inner_text(timeout=2000)
        href = link.get_attribute("href") or ""
        if href.startswith("http"):
            yield cite_text, href

    # Fallback when Google DOM differs (no data-rpos blocks)
    for block in page.locator("#search .g, #rso .g").all():
        cite_el = block.locator("cite").first
        link = block.locator("a[href^='http']").first
        if cite_el.count() == 0 or link.count() == 0:
            continue
        cite_text = cite_el.inner_text(timeout=2000)
        href = link.get_attribute("href") or ""
        if href.startswith("http"):
            yield cite_text, href


def google_search_product_url(
    page,
    mpn: str,
    *,
    google_cite: str,
    log: Callable[[str], None] = print,
    wait_for_captcha: Callable[[], None] | None = None,
) -> str | None:
    """
    Search Google for ``{mpn} site:{domain}`` and return the first organic
    result whose cite matches ``google_cite``.

    Iterates ``#center_col #rso div[data-rpos]`` blocks (user XPath spec):
      cite text from ``div[data-snhf="0"] cite``
      href from ``div[data-snhf="0"] span a``
    """
    domain = _normalize_cite(google_cite)
    query = f"{mpn} site:{domain}"
    search_url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"
    log(f"Google SEARCH -> {search_url}")

    page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)

    if _is_google_blocked(page):
        log("Google: blocked by captcha / unusual-traffic page")
        if wait_for_captcha:
            wait_for_captcha()
        else:
            from core.scrape_ui import get_captcha_waiter

            get_captcha_waiter().wait(log=log)

    seen = set()
    for i, (cite_text, href) in enumerate(_iter_google_results(page), start=1):
        key = (cite_text, href)
        if key in seen:
            continue
        seen.add(key)
        log(f"Google [{i}] cite: {cite_text!r}")
        if _cite_matches(cite_text, google_cite):
            log(f"Google FOUND -> {href}")
            return href

    log(f"Google: no result matching cite {google_cite!r} for {mpn}")
    return None
