from playwright.sync_api import sync_playwright


def get_browser():
    p = sync_playwright().start()
    browser = None
    try:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            )
        )
        return p, browser, page
    except BaseException:
        try:
            if browser is not None:
                browser.close()
        finally:
            p.stop()
        raise
