from playwright.sync_api import TimeoutError


def wait_until_loaded(
    page,
    selectors=None,
    timeout=30000, #5mins timeout
    extra_wait=3000 #30s wait
):

    selectors = selectors or []

    for selector in selectors:

        try:

            print(f"WAIT -> {selector}")

            page.wait_for_selector(
                selector,
                timeout=timeout
            )

        except TimeoutError:

            print(
                f"TIMEOUT -> {selector}"
            )

    page.wait_for_timeout(
        extra_wait
    )