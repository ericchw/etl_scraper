from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.cache import resolve_product_json_path
from core.categories import load_categories
from core.ehf import load_ehf_profiles
from core.exporter import export_bestbuy_laptop, export_newegg
from core.app_settings import download_product_images_enabled
from core.marketplace_defaults import bestbuy_discount_dates
from core.merge_policy import load_merge_sources
from core.pipeline import dedupe_jobs_by_mpn, run_batch_pipeline, use_existing_scrape
from core.utils import load_json
from core.marketplace_templates import ensure_mapping_yaml, migrate_legacy_templates
from gui.scrape_item_panel import ScrapeItemPanel
from gui.source_priority_dialog import SourcePriorityDialog

ROOT = Path(__file__).resolve().parent.parent


class ScrapeThread(QThread):
    finished = pyqtSignal(dict)
    log_line = pyqtSignal(str)

    def __init__(self, items: list[dict], *, rescrape: bool) -> None:
        super().__init__()
        self._items = items
        self._rescrape = rescrape

    def run(self) -> None:
        def log(msg: str) -> None:
            self.log_line.emit(str(msg))

        jobs = [{**item, "rescrape": self._rescrape} for item in self._items]
        try:
            self.finished.emit(run_batch_pipeline(jobs, log=log))
        except Exception as exc:  # noqa: BLE001
            self.log_line.emit(str(exc))
            self.finished.emit({"success": False, "error": str(exc)})


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ETL Scraper")
        self.resize(780, 720)
        self.setStyleSheet(
            """
            QWidget { font-size: 11px; }
            QLineEdit, QComboBox, QDoubleSpinBox {
                min-height: 22px; padding: 2px 6px;
            }
            QPushButton { min-height: 26px; padding: 4px 10px; }
            QTextEdit { font-size: 10px; background: #1a1a1a; }
            """
        )

        self._thread: ScrapeThread | None = None
        self._item_index = 0
        self._items: list[ScrapeItemPanel] = []
        self._categories = load_categories()
        self._ehf_profiles = load_ehf_profiles()

        self._items_layout = QVBoxLayout()
        self._items_layout.setSpacing(8)
        self._items_layout.setContentsMargins(8, 8, 8, 8)
        self._items_layout.addStretch()

        self._add_btn = QPushButton("+ Add item")
        self._add_btn.setStyleSheet(
            "background: #2563eb; color: white; font-weight: 600; border: none; border-radius: 6px;"
        )
        self._add_btn.clicked.connect(self._add_item)

        scroll_inner = QWidget()
        scroll_inner.setLayout(self._items_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_inner)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setFixedSize(32, 32)
        self._settings_btn.setToolTip(
            "Settings: source priority, download photos, discount dates"
        )
        self._settings_btn.clicked.connect(self._open_source_settings)

        title = QLabel("ETL Scraper")
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._settings_btn)

        self._run_btn = QPushButton("Run scrape")
        self._export_btn = QPushButton("Export all")
        self._run_btn.setStyleSheet("background: #16a34a; color: white; font-weight: 600;")
        self._export_btn.setStyleSheet("background: #ea580c; color: white; font-weight: 600;")
        self._run_btn.clicked.connect(self._on_run)
        self._export_btn.clicked.connect(self._on_export_all)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._run_btn)
        btn_row.addWidget(self._export_btn)

        self._log_toggle = QPushButton("Show log")
        self._log_toggle.setCheckable(True)
        self._log_toggle.setChecked(False)
        self._log_toggle.toggled.connect(self._toggle_log)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(80)
        self._log.setVisible(False)

        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("Log"))
        log_header.addStretch()
        log_header.addWidget(self._log_toggle)

        log_wrap = QWidget()
        log_layout = QVBoxLayout(log_wrap)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addLayout(log_header)
        log_layout.addWidget(self._log)

        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.addWidget(scroll)
        self._splitter.addWidget(log_wrap)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self._log_pane_visible = False
        self._splitter.setSizes([600, 0])

        # migrate_legacy_templates()

        root = QVBoxLayout(self)
        root.addLayout(header)
        root.addWidget(self._splitter, stretch=1)
        root.addLayout(btn_row)

        self._add_item()

    def _place_add_button(self) -> None:
        """Keep + Add item directly under the last item row."""
        self._items_layout.removeWidget(self._add_btn)
        idx = max(0, self._items_layout.count() - 1)
        self._items_layout.insertWidget(idx, self._add_btn)

    def _add_item(self) -> None:
        self._item_index += 1
        panel = ScrapeItemPanel(
            index=self._item_index,
            categories=self._categories,
            ehf_profiles=self._ehf_profiles,
        )
        panel.removed.connect(self._remove_item)
        idx = max(0, self._items_layout.count() - 1)
        self._items_layout.insertWidget(idx, panel)
        self._items.append(panel)
        self._place_add_button()

    def _remove_item(self, panel: ScrapeItemPanel) -> None:
        if len(self._items) <= 1:
            QMessageBox.information(self, "Cannot remove", "Keep at least one item.")
            return
        self._items.remove(panel)
        self._items_layout.removeWidget(panel)
        panel.setParent(None)
        panel.deleteLater()
        self._place_add_button()

    def _toggle_log(self, visible: bool) -> None:
        log_wrap = self._splitter.widget(1)
        self._log_pane_visible = visible
        self._log_toggle.blockSignals(True)
        self._log_toggle.setChecked(visible)
        self._log_toggle.setText("Hide log" if visible else "Show log")
        self._log_toggle.blockSignals(False)

        log_wrap.setVisible(True)
        self._log.setVisible(True)
        total = max(sum(self._splitter.sizes()), self._splitter.height(), 400)
        if visible:
            self._splitter.setSizes([int(total * 0.72), int(total * 0.28)])
        else:
            self._splitter.setSizes([total, 0])

    def _open_source_settings(self) -> None:
        if SourcePriorityDialog(self).exec():
            cfg = load_merge_sources()
            start, end = bestbuy_discount_dates()
            dl = "on" if download_product_images_enabled() else "off"
            self._append_log(
                f"Settings saved · download photos {dl} · discount {start} → {end}"
            )

    def _all_scrape_errors(self) -> list[str]:
        errors: list[str] = []
        for panel in self._items:
            errors.extend(panel.validation_errors_scrape())
        return errors

    def _all_export_errors(self) -> list[str]:
        errors: list[str] = []
        for panel in self._items:
            errors.extend(panel.validation_errors_export())
        return errors

    def _collect_jobs(self) -> list[dict]:
        return [job for panel in self._items if (job := panel.to_job())]

    def _cached_mpns(self, jobs: list[dict]) -> list[str]:
        found: list[str] = []
        for job in dedupe_jobs_by_mpn(jobs):
            mpn = job["mpn"]
            if resolve_product_json_path(mpn) and mpn not in found:
                found.append(mpn)
        return found

    def _prompt_existing_json(self, mpns: list[str]) -> str | None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Existing scrape data")
        box.setText(f"Found saved product JSON for: {', '.join(mpns)}")
        box.setInformativeText(
            "Use existing: load products/{MPN}.json only (no browser scrape). "
            "Scrape again: refresh all sources once per MPN."
        )
        use_btn = box.addButton("Use existing JSON", QMessageBox.ButtonRole.AcceptRole)
        scrape_btn = box.addButton("Scrape again", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(use_btn)
        box.exec()
        clicked = box.clickedButton()
        if clicked is cancel_btn or clicked is None:
            return None
        if clicked is use_btn:
            return "use_existing"
        return "rescrape"

    def _on_run(self) -> None:
        errors = self._all_scrape_errors()
        if errors:
            QMessageBox.warning(self, "Validation", "\n".join(errors))
            return
        jobs = self._collect_jobs()
        if not jobs:
            QMessageBox.warning(self, "Nothing to scrape", "Fix validation errors on items.")
            return
        if self._thread and self._thread.isRunning():
            return

        cached = self._cached_mpns(jobs)
        rescrape = False
        if cached:
            choice = self._prompt_existing_json(cached)
            if choice is None:
                return
            if choice == "use_existing":
                self._log.clear()
                for job in dedupe_jobs_by_mpn(jobs):
                    result = use_existing_scrape(
                        job["mpn"],
                        submission=job.get("submission"),
                        log=self._append_log,
                    )
                    if not result.get("success"):
                        self._append_log(
                            f"{job['mpn']}: load failed — {result.get('error', 'unknown')}"
                        )
                QMessageBox.information(
                    self,
                    "Ready",
                    "Loaded existing JSON (one file per MPN). Export each row separately.",
                )
                return
            rescrape = True

        unique = dedupe_jobs_by_mpn(jobs)
        self._run_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._log.clear()
        if len(unique) < len(jobs):
            self._append_log(
                f"Scraping {len(unique)} unique MPN(s) from {len(jobs)} item row(s)…"
            )
        else:
            self._append_log(f"Scraping {len(jobs)} item(s)…")
        self._thread = ScrapeThread(jobs, rescrape=rescrape)
        self._thread.log_line.connect(self._append_log)
        self._thread.finished.connect(self._on_scrape_finished)
        self._thread.start()

    def _on_scrape_finished(self, result: dict) -> None:
        self._run_btn.setEnabled(True)
        self._export_btn.setEnabled(True)
        self._thread = None
        if result.get("success"):
            ui = result.get("ui_items", result.get("total"))
            self._append_log(
                f"Done {result.get('completed')}/{result.get('total')} MPN(s) "
                f"({ui} item row(s))"
            )
            QMessageBox.information(
                self,
                "Done",
                "Scrape finished. Product JSON saved under products/.",
            )
        else:
            QMessageBox.critical(self, "Scrape failed", result.get("error", "See log"))

    def _on_export_all(self) -> None:
        errors = self._all_export_errors()
        if errors:
            QMessageBox.warning(self, "Validation", "\n".join(errors))
            return

        exported = 0
        for panel in self._items:
            mpn = panel._mpn.text().strip().upper()
            if not mpn:
                continue
            path = resolve_product_json_path(mpn)
            if not path:
                self._append_log(f"Skip {mpn}: no product JSON — run scrape first")
                continue
            product = load_json(str(path))
            product["submission"] = panel.to_submission()
            self._export_one(product, mpn)
            exported += 1

        if exported == 0:
            QMessageBox.warning(self, "Export", "No items exported. Scrape first or fix validation.")
        else:
            QMessageBox.information(self, "Export", f"Exported {exported} item(s). See log.")

    def _export_one(self, product: dict, mpn: str) -> None:
        submission = product.get("submission") or {}
        category_key = submission.get("category") or "gaming_laptop"
        log = self._append_log

        if submission.get("marketplaces", {}).get("bestbuy", {}).get("enabled"):
            mapping, _, created = ensure_mapping_yaml(category_key, "bestbuy", log=log)
            if created and mapping:
                log(f"Generated Best Buy mapping {mapping.name}")

            try:
                out, warnings = export_bestbuy_laptop(product, log=log)
                log(f"Best Buy {mpn} → {out}")
                for w in warnings:
                    log(f"  WARN: {w}")
            except Exception as exc:
                log(f"Best Buy {mpn} failed: {exc}")

        if submission.get("marketplaces", {}).get("newegg", {}).get("enabled"):
            mapping, _, created = ensure_mapping_yaml(category_key, "newegg", log=log)
            if created and mapping:
                log(f"Generated Newegg mapping {mapping.name}")

            try:
                out, warnings = export_newegg(product, log=log)
                log(f"Newegg {mpn} → {out}")
                for w in warnings:
                    log(f"  WARN: {w}")
            except Exception as exc:
                log(f"Newegg {mpn} failed: {exc}")

    def _append_log(self, text: str) -> None:
        if not self._log_pane_visible:
            self._toggle_log(True)
        self._log.append(text)


def run_app() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
