"""Regression checks for filesystem safety, settings, and browser cleanup."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

from core import app_settings, cache


class ProductPathTests(unittest.TestCase):
    def test_real_mpn_is_preserved(self):
        self.assertEqual(cache.product_path(" 9w3e2ua#abl ").name, "9W3E2UA#ABL.json")

    def test_unsafe_ids_are_rejected_by_all_product_paths(self):
        for value in ("", "../outside", "..\\outside", "C:\\outside", "x:y", "NUL", "CON.txt", "COM¹", "CONOUT$", "part.", "bad\x00id"):
            for make_path in (cache.product_path, cache.legacy_json_path,
                              lambda mpn: cache.cache_raw_path("cdw", mpn),
                              lambda mpn: cache.cache_meta_path("cdw", mpn)):
                with self.subTest(value=value, function=make_path):
                    with self.assertRaises(ValueError):
                        make_path(value)

    def test_cache_source_cannot_escape_cache_directory(self):
        with self.assertRaises(ValueError):
            cache.cache_raw_path("../outside", "DYFPN")


class SettingsTests(unittest.TestCase):
    def test_missing_malformed_and_non_object_settings_use_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            with patch.object(app_settings, "SETTINGS_PATH", path):
                self.assertEqual(app_settings.load_app_settings(), app_settings.DEFAULTS)
                for data in ("{broken", "[]", "null"):
                    path.write_text(data, encoding="utf-8")
                    self.assertEqual(app_settings.load_app_settings(), app_settings.DEFAULTS)

    def test_saving_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"other": 42}), encoding="utf-8")
            with patch.object(app_settings, "SETTINGS_PATH", path):
                app_settings.save_app_settings({"download_product_images": True})
                self.assertEqual(app_settings.load_app_settings(), {
                    "other": 42, "download_product_images": True,
                })


class BrowserCleanupTests(unittest.TestCase):
    def test_startup_failure_stops_playwright(self):
        for failure in ("launch", "new_page"):
            with self.subTest(failure=failure):
                runtime = MagicMock()
                browser = runtime.chromium.launch.return_value
                target = runtime.chromium.launch if failure == "launch" else browser.new_page
                target.side_effect = RuntimeError("startup failed")
                api = types.ModuleType("playwright.sync_api")
                api.sync_playwright = MagicMock()
                api.sync_playwright.return_value.start.return_value = runtime
                spec = importlib.util.spec_from_file_location("browser_under_test", Path(__file__).resolve().parents[1] / "core/browser.py")
                module = importlib.util.module_from_spec(spec)
                with patch.dict(sys.modules, {"playwright.sync_api": api}):
                    spec.loader.exec_module(module)
                with self.assertRaisesRegex(RuntimeError, "startup failed"):
                    module.get_browser()
                runtime.stop.assert_called_once()
                if failure == "new_page":
                    browser.close.assert_called_once()

    def test_success_leaves_resources_open_for_caller(self):
        runtime = MagicMock()
        api = types.ModuleType("playwright.sync_api")
        api.sync_playwright = MagicMock()
        api.sync_playwright.return_value.start.return_value = runtime
        spec = importlib.util.spec_from_file_location("browser_under_test", Path(__file__).resolve().parents[1] / "core/browser.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"playwright.sync_api": api}):
            spec.loader.exec_module(module)
        p, browser, page = module.get_browser()
        self.assertIs(p, runtime)
        self.assertIs(page, browser.new_page.return_value)
        browser.close.assert_not_called()
        runtime.stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
