"""Settings: source priority + Best Buy discount dates."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
)

from gui.discount_dates_widget import DiscountDatesWidget
from gui.scrape_options_widget import ScrapeOptionsWidget
from gui.source_priority_widget import SourcePriorityWidget


class SourcePriorityDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(720, 420)
        self.resize(860, 480)

        self._sources = SourcePriorityWidget()
        self._scrape_options = ScrapeOptionsWidget()
        self._discounts = DiscountDatesWidget()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._sources)
        layout.addWidget(self._scrape_options)
        layout.addWidget(self._discounts)
        layout.addWidget(buttons)

    def _on_save(self) -> None:
        self._sources.save()
        self._scrape_options.save()
        self._discounts.save()
        self.accept()
