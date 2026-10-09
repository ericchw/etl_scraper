"""
Scrape → normalize → products/{mpn}.json (scraped_data + internal).

Source list and merge priority come from configs/merge_sources.json.
Raw per-site blobs live in product JSON scraped_data only (no cache/ folder).
"""

from __future__ import annotations

from typing import Callable

from core.browser import get_browser
from core.cache import (
    legacy_json_path,
    load_product_scraped_data,
    product_path,
    resolve_product_json_path,
)
from core.downloader import download_images
from core.paths import safe_path_component
from core.merge_policy import (
    format_merge_priority_log,
    manufacturer_config,
    scrape_visit_order,
    should_scrape_source,
)
from core.app_settings import download_product_images_enabled
from core.normalizer import build_product_document, resolve_product_code
from core.schema.registry import DEFAULT_PRODUCT_CODE
from core.product_document import finalize_product_document
from core.scraper_registry import load_scraper_config
from core.utils import load_json, save_json
from sites.cdw.search import search_cdw_product
from sites.cdw.scraper import scrape_cdw_product

import traceback

def scraped_json_path(mpn: str) -> str:
    key = safe_path_component((mpn or "").upper())
    return f"products/{key}.json"


def _scrape_cdw(page, mpn: str, *, log: Callable[[str], None]) -> tuple[dict | None, str]:
    cdw_url = search_cdw_product(page, mpn, log=log)
    if not cdw_url:
        log("CDW: product not found")
        return None, ""
    page.goto(cdw_url, wait_until="domcontentloaded", timeout=60000)
    product = scrape_cdw_product(page)
    return product, cdw_url


def _scrape_manufacturer(
    page,
    mpn: str,
    *,
    submission: dict | None,
    log: Callable[[str], None],
    wait_for_captcha: Callable[[], None] | None = None,
) -> tuple[dict | None, str]:
    brand = (submission or {}).get("manufacturer", "").strip()
    cfg = manufacturer_config(brand)
    if not cfg:
        log(f"Manufacturer: no config for {brand!r}")
        return None, ""
    if cfg.get("enabled") is False:
        log(f"Manufacturer {brand}: disabled in manufacturers.json")
        return None, ""

    brand_key = brand.lower().replace(" ", "_")
    has_search = bool((cfg.get("search_url") or "").strip())
    has_google = bool(cfg.get("google_search")) and bool((cfg.get("google_cite") or "").strip())
    if not has_search and not has_google:
        log(f"Manufacturer {brand}: no search_url or google_search configured")
        return None, ""

    from sites.manufacturers.search import resolve_manufacturer_product_url

    product_url = resolve_manufacturer_product_url(
        page,
        mpn,
        cfg,
        brand_key=brand_key,
        log=log,
        wait_for_captcha=wait_for_captcha,
    )
    if not product_url:
        log(f"Manufacturer {brand}: product not found")
        return None, ""

    if page.url != product_url:
        log(f"Manufacturer PDP -> {product_url}")
        page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

    if brand_key == "dell":
        from sites.manufacturers.dell import scrape_dell_product

        raw = scrape_dell_product(page)
        raw["mpn"] = mpn.upper()
        return raw, product_url

    if brand_key == "arctic":
        from sites.manufacturers.arctic import scrape_arctic_product

        raw = scrape_arctic_product(page)
        raw["mpn"] = mpn.upper()
        return raw, product_url

    log(f"Manufacturer scraper for {brand!r} not implemented yet")
    return {"source": "manufacturer", "mpn": mpn.upper(), "specs": {}}, product_url


def _scrape_source(
    source: str,
    page,
    mpn: str,
    *,
    submission: dict | None,
    log: Callable[[str], None],
    wait_for_captcha: Callable[[], None] | None = None,
) -> tuple[dict | None, str]:
    cfg = load_scraper_config(source)
    if cfg.get("enabled") is False:
        log(f"{source.upper()}: disabled in scraper config")
        return None, ""

    if source == "cdw":
        return _scrape_cdw(page, mpn, log=log)

    if source == "bh":
        from sites.bh.scraper import scrape_bh_product

        product = scrape_bh_product(page, mpn, log=log)
        return product, ""

    if source == "manufacturer":
        return _scrape_manufacturer(
            page,
            mpn,
            submission=submission,
            log=log,
            wait_for_captcha=wait_for_captcha,
        )

    log(f"Unknown source: {source}")
    return None, ""


def use_existing_scrape(
    mpn: str,
    *,
    submission: dict | None = None,
    log: Callable[[str], None] = print,
) -> dict:
    mpn_key = (mpn or "").strip().upper()
    if not mpn_key:
        return {"success": False, "error": "MISSING_MPN"}

    path = resolve_product_json_path(mpn_key)
    existing = load_json(str(path)) if path else None
    scraped = (existing or {}).get("scraped_data") if isinstance(existing, dict) else None

    if isinstance(scraped, dict) and any(scraped.values()):
        raw_by_source = {src: raw for src, raw in scraped.items() if raw}
        code = resolve_product_code(
            explicit=(existing or {}).get("product_code"),
            submission=submission,
            existing_doc=existing,
        )
        product = build_product_document(
            raw_by_source,
            product_code=code,
            submission=submission,
        )
        log(
            f"Rebuilt internal ({code}) from products/{mpn_key}.json scraped_data "
            f"({len(raw_by_source)} source(s))"
        )
    elif path and existing:
        product = finalize_product_document(existing)
        log(f"LOAD PRODUCT (no scraped_data to rebuild) -> {path}")
    else:
        leg = legacy_json_path(mpn_key)
        if leg.exists():
            legacy = load_json(str(leg))
            raw_by_source = {
                "cdw": {
                    "source": "cdw",
                    "title": legacy.get("title"),
                    "mpn": legacy.get("mpn"),
                    "description": legacy.get("description"),
                    "features": legacy.get("features"),
                    "images": legacy.get("images"),
                    "specs": legacy.get("specs") or {},
                }
            }
            code = resolve_product_code(submission=submission)
            product = build_product_document(
                raw_by_source,
                product_code=code,
                submission=submission,
            )
            log(f"Migrated legacy JSON -> products/{mpn_key}.json")
        else:
            return {"success": False, "error": "FILE_NOT_FOUND"}

    out = product_path(mpn_key)
    save_json(product, str(out), log=log)
    return {
        "success": True,
        "reused": True,
        "normalized": product,
        "submission": submission,
        "paths": {"json": str(out)},
    }


def run_product_pipeline(
    mpn: str,
    *,
    submission: dict | None = None,
    product_code: str | None = None,
    rescrape: bool = False,
    download_product_images: bool = False,
    log: Callable[[str], None] = print,
    wait_for_captcha: Callable[[], None] | None = None,
) -> dict:
    mpn_key = (mpn or "").strip().upper()
    if not mpn_key:
        return {"success": False, "error": "MISSING_MPN"}

    sources = scrape_visit_order()
    raw_by_source: dict[str, dict] = {}
    paths: dict = {}

    existing_doc = None
    existing_path = resolve_product_json_path(mpn_key)
    if existing_path:
        existing_doc = load_json(str(existing_path))

    code = resolve_product_code(
        explicit=product_code,
        submission=submission,
        existing_doc=existing_doc,
    )

    log(f"Product family: {code}")
    log(f"Merge priority — {format_merge_priority_log()}")
    log(f"Scrape visit order: {' -> '.join(sources)}")

    if not rescrape:
        stored = load_product_scraped_data(mpn_key)
        if stored:
            raw_by_source.update(stored)
            log(
                f"PRELOAD products/{mpn_key}.json scraped_data "
                f"({', '.join(sorted(raw_by_source))})"
            )

    needs_browser = rescrape or any(
        should_scrape_source(
            s,
            mpn_key=mpn_key,
            rescrape=rescrape,
            raw_by_source=raw_by_source,
            submission=submission,
        )[0]
        for s in sources
    )

    p = browser = page = None
    try:
        if needs_browser:
            p, browser, page = get_browser()

        for source in sources:
            do_scrape, reason = should_scrape_source(
                source,
                mpn_key=mpn_key,
                rescrape=rescrape,
                raw_by_source=raw_by_source,
                submission=submission,
            )
            if not do_scrape:
                log(f"SKIP {source.upper()} ({reason})")
                continue

            if page is None:
                continue

            log(f"SCRAPE {source.upper()} ({reason}) …")
            raw, _url = _scrape_source(
                source,
                page,
                mpn_key,
                submission=submission,
                log=log,
                wait_for_captcha=wait_for_captcha,
            )
            if raw:
                raw["mpn"] = raw.get("mpn") or mpn_key
                raw_by_source[source] = raw
            elif source == "cdw":
                log("CDW: no data — will try B&H for spec/packing per merge config")

        if not raw_by_source:
            return {"success": False, "error": "NO_SOURCE_DATA"}

        product = build_product_document(
            raw_by_source,
            product_code=code,
            submission=submission,
        )

        json_path = product_path(mpn_key)
        save_json(product, str(json_path), log=log)
        paths["json"] = str(json_path)

        content = (product.get("internal") or {}).get("content") or {}
        images = (
            content.get("images")
            or product.get("images")
            or product.get("scraped_image_urls")
            or []
        )
        if download_product_images and images:
            img_dir = f"output/images/{mpn_key}"
            downloaded = download_images(images, img_dir, mpn_key, log=log)
            paths["images_dir"] = img_dir
            paths["image_files"] = downloaded

        return {
            "success": True,
            "normalized": product,
            "submission": submission,
            "paths": paths,
            "merge_report": product.get("merge_report", {}),
        }

    except Exception as exc:  # noqa: BLE001
        log(f"ERROR: {exc}")
        traceback.print_exc()
        return {"success": False, "error": str(exc)}

    finally:
        try:
            if browser:
                browser.close()
        finally:
            if p:
                p.stop()


def run_cdw_pipeline(
    mpn: str,
    *,
    submission: dict | None = None,
    download_product_images: bool = True,
    log: Callable[[str], None] = print,
) -> dict:
    return run_product_pipeline(
        mpn,
        submission=submission,
        download_product_images=download_product_images,
        log=log,
    )


def dedupe_jobs_by_mpn(items: list[dict]) -> list[dict]:
    """One scrape job per MPN (first item wins; tracks how many UI rows share it)."""
    by_mpn: dict[str, dict] = {}
    for item in items:
        mpn = (item.get("mpn") or "").strip().upper()
        if not mpn:
            continue
        if mpn not in by_mpn:
            by_mpn[mpn] = {
                **item,
                "mpn": mpn,
                "product_code": item.get("product_code") or DEFAULT_PRODUCT_CODE,
                "item_count": 1,
            }
        else:
            by_mpn[mpn]["item_count"] = int(by_mpn[mpn].get("item_count", 1)) + 1
    return list(by_mpn.values())


def run_batch_pipeline(
    items: list[dict],
    *,
    log: Callable[[str], None] = print,
    wait_for_captcha: Callable[[], None] | None = None,
) -> dict:
    """
    Each item: {"mpn": "...", "submission": {...}, "rescrape": bool optional}.

    Duplicate MPNs in the queue only trigger one browser scrape; export uses each
    row's submission (e.g. open box vs not).
    """
    jobs = dedupe_jobs_by_mpn(items)
    results = []
    ok = 0
    for job in jobs:
        mpn = job["mpn"]
        count = int(job.get("item_count", 1))
        log(f"--- MPN {mpn} ---")
        result = run_product_pipeline(
            mpn,
            submission=job.get("submission"),
            product_code=job.get("product_code"),
            rescrape=bool(job.get("rescrape")),
            download_product_images=download_product_images_enabled(),
            log=log,
            wait_for_captcha=wait_for_captcha,
        )
        results.append({"mpn": mpn, "item_count": count, **result})
        if result.get("success"):
            ok += 1
    return {
        "success": ok > 0 and ok == len(jobs),
        "completed": ok,
        "total": len(jobs),
        "ui_items": len(items),
        "results": results,
    }
