from core.waits import wait_until_loaded
from urllib.parse import urlsplit, urlunsplit
import re

def scrape_cdw_product(page):

    wait_until_loaded(
        page,
        selectors=[
            "#primaryProductNameStickyHeader",
            ".accordion.tech-spec-accordion"
        ]
    )

    def text(selector):

        el = page.query_selector(selector)

        if not el:
            return ""

        return el.inner_text().strip()

    title = text(
        "#primaryProductNameStickyHeader"
    )

    mpn = text("span.mpn")

    description = text(
        '[itemprop="description"]'
    )

    category = ""

    crumbs = page.query_selector_all(
        'span[itemprop="name"]'
    )

    if crumbs:

        category = (
            crumbs[-1]
            .inner_text()
            .strip()
        )

    # =========================
    # images (carousel-aware)
    # =========================
    def clean_cdw_image_url(url: str) -> str:
        if not url:
            return ""

        # fix protocol-relative
        if url.startswith("//"):
            url = "http:" + url  # you requested http output

        # remove CDW rendering suffix ($....$)
        url = re.sub(r"\$.*$", "", url)

        # remove query params if any appear
        url = url.split("?")[0]

        return url

    image_urls = []

    # ensure main image is clicked first
    main_img = page.query_selector(".main-image")
    if main_img:
        try:
            main_img.click()
            print("CDW clicked main_img")
        except Exception as e:
            print("CDW main_img erorr:", e)
            pass

    selector = (
        ".thumbnails-tabs-container .slick-list.draggable button.thumb, "
        ".thumbnails-tabs-container .slide-thumb button.thumb"
    )

    thumbs = page.locator(selector)

    try:
        thumbs.first.wait_for(timeout=15000)
    except Exception:
        pass

    for i in range(thumbs.count()):
        btn = thumbs.nth(i)

        try:
            raw = btn.get_attribute("data-imageurl", timeout=5000)
        except Exception:
            continue

        if raw:
            image_urls.append(clean_cdw_image_url(raw))

    image_urls = list(dict.fromkeys(image_urls))

    # =========================
    # features
    # =========================

    features = []

    feature_rows = page.query_selector_all(
        '.quick-tech-spec-row li'
    )

    for li in feature_rows:

        txt = li.inner_text().strip()

        if txt:
            features.append(txt)

    # =========================
    # specs
    # =========================

    specs = {}

    sections = page.query_selector_all(
        '.accordion.tech-spec-accordion .accordion-row'
    )

    for section in sections:

        title_el = section.query_selector(
            'button .accordion-title'
        )

        if not title_el:
            continue

        group_name = (
            title_el
            .inner_text()
            .strip()
        )

        specs[group_name] = {}

        rows = section.query_selector_all(
            '.panel-row'
        )

        for row in rows:

            key_el = row.query_selector(
                '.title'
            )

            val_el = row.query_selector(
                '.desc'
            )

            if not key_el or not val_el:
                continue

            key = (
                key_el
                .inner_text()
                .strip()
            )

            value = (
                val_el
                .inner_text()
                .strip()
            )

            specs[group_name][key] = value

    product = {

        "source": "cdw",

        "category": category,

        "title": title,

        "mpn": mpn,

        "description": description,

        "features": features,

        "images": image_urls,

        "specs": specs
    }

    return product