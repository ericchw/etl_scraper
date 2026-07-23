"""UI hooks for long-running scrape operations (e.g. Google captcha)."""

from __future__ import annotations

import threading
from typing import Callable


class CaptchaWaiter:
    """Block scrape thread until user resolves captcha in the browser."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._request_ui: Callable[[], None] | None = None

    def configure(self, request_ui: Callable[[], None]) -> None:
        """``request_ui`` must schedule a main-thread dialog (e.g. Qt signal emit)."""
        self._request_ui = request_ui

    def wait(self, *, log: Callable[[str], None] = print) -> None:
        log("Google: captcha detected — waiting for user to resolve…")
        self._event.clear()
        if self._request_ui:
            self._request_ui()
        else:
            input("Resolve captcha in the browser, then press Enter to continue…")
        self._event.wait()
        log("Google: continuing after captcha resolved")

    def release(self) -> None:
        self._event.set()


_waiter = CaptchaWaiter()


def get_captcha_waiter() -> CaptchaWaiter:
    return _waiter
