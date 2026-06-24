"""Scrape options (saved to configs/app_settings.json)."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QVBoxLayout,
    QWidget,
)

from core.app_settings import load_app_settings, save_app_settings


class ScrapeOptionsWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        box = QGroupBox("Scrape options")
        self._download_images = QCheckBox("Download product photos after scrape")
        self._download_images.setToolTip(
            "Saves merged image URLs to output/images/{MPN}/ during Run scrape. "
            "Does not run when using existing JSON only."
        )
        inner = QVBoxLayout()
        inner.addWidget(self._download_images)
        box.setLayout(inner)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(box)
        self.reload()

    def reload(self) -> None:
        cfg = load_app_settings()
        self._download_images.setChecked(bool(cfg.get("download_product_images")))

    def save(self) -> None:
        save_app_settings(
            {"download_product_images": self._download_images.isChecked()}
        )
