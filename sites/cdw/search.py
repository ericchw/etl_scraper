from core.waits import wait_until_loaded


def search_cdw_product(
    page,
    mpn,
    log=print,
):

    search_url = (
        f"https://www.cdw.ca/search/?key={mpn}"
    )

    log(f"SEARCH -> {search_url}")

    page.goto(
        search_url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(3000)

    current_url = page.url.lower()

    # -------------------------------------------------
    # CDW redirected away from search page
    # Means product was found directly
    # -------------------------------------------------

    if "/search/" not in current_url:

        log(
            f"REDIRECT PRODUCT -> {page.url}"
        )

        return page.url

    # -------------------------------------------------
    # Still on search page
    # Need to inspect search results
    # -------------------------------------------------

    wait_until_loaded(
        page,
        selectors=[
            ".search-result"
        ]
    )

    results = page.query_selector_all(
        ".search-result"
    )

    for result in results:

        code_block = result.query_selector(
            ".product-codes"
        )

        if not code_block:
            continue

        text = code_block.inner_text()

        if mpn.lower() in text.lower():

            link = result.query_selector(
                "h2 a"
            )

            if not link:
                continue

            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            if href.startswith("/"):

                href = (
                    "https://www.cdw.ca"
                    + href
                )

            log(
                f"FOUND -> {href}"
            )

            return href

    log(
        f"Unable to find search result of {mpn}"
    )

    return None