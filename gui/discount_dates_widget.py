"""Best Buy discount window editor (saved to marketplace_defaults.json)."""

from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QDateEdit,
)

from core.marketplace_defaults import load_defaults, save_defaults


class DiscountDatesWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        box = QGroupBox("Best Buy discount dates")
        self._start = QDateEdit()
        self._start.setCalendarPopup(True)
        self._start.setDisplayFormat("yyyy-MM-dd")
        self._end = QDateEdit()
        self._end.setCalendarPopup(True)
        self._end.setDisplayFormat("yyyy-MM-dd")
        # self._duration = QSpinBox()
        # self._duration.setRange(1, 365)
        # self._duration.setSuffix(" days")
        # self._duration.setToolTip("Used when end date is left empty in config file")

        form = QFormLayout()
        form.addRow("Discount start", self._start)
        form.addRow("Discount end", self._end)
        # form.addRow("Default span (if end blank)", self._duration)
        box.setLayout(form)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(box)
        self.reload()

    def reload(self) -> None:
        bb = load_defaults().get("bestbuy") or {}
        start_s = str(bb.get("discount_start_date") or "").strip()
        end_s = str(bb.get("discount_end_date") or "").strip()
        today = QDate.currentDate()
        if start_s:
            y, m, d = (int(x) for x in start_s.split("-"))
            self._start.setDate(QDate(y, m, d))
        else:
            self._start.setDate(today)
        if end_s:
            y, m, d = (int(x) for x in end_s.split("-"))
            self._end.setDate(QDate(y, m, d))
        # else:
        #     self._end.setDate(today.addDays(int(bb.get("discount_duration_days") or 30)))
        # self._duration.setValue(int(bb.get("discount_duration_days") or 30))

    def save(self) -> None:
        save_defaults(
            {
                "discount_start_date": self._start.date().toString("yyyy-MM-dd"),
                "discount_end_date": self._end.date().toString("yyyy-MM-dd"),
                # "discount_duration_days": self._duration.value(),
            }
        )
