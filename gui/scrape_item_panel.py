"""One queue row: category → MPN → Newegg / Best Buy."""

from __future__ import annotations

from PyQt6.QtCore import QRegularExpression, Qt, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.categories import marketplace_code, product_code, sku_prefix
from core.marketplace_defaults import bestbuy_discount_dates
from core.merge_policy import load_manufacturers
from core.conditions import load_conditions
from core.pricing import bestbuy_list_price_from_discount

COMPACT_STYLE = """
QLineEdit, QComboBox, QDoubleSpinBox {
    min-height: 22px;
    max-height: 26px;
    padding: 2px 6px;
    font-size: 11px;
}
QGroupBox { font-size: 11px; padding: 6px; margin-top: 6px; }
"""


class ScrapeItemPanel(QGroupBox):
    removed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(
        self,
        *,
        index: int,
        categories: dict,
        ehf_profiles: dict,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._index = index
        self._expanded = True
        self.setStyleSheet(COMPACT_STYLE)

        self._category = QComboBox()
        self._category.addItem("— select —", userData="")
        for key, data in categories.items():
            if isinstance(data, dict) and data.get("enable", True) is False:
                continue
            self._category.addItem(data.get("label", key), userData=key)

        self._manufacturer = QComboBox()
        self._manufacturer.addItem("— select —", userData="")
        for key, cfg in sorted(load_manufacturers().items()):
            label = cfg.get("label", key.title()) if isinstance(cfg, dict) else key.title()
            self._manufacturer.addItem(label, userData=key)

        self._mpn = QLineEdit()
        self._mpn.setPlaceholderText("MPN")
        self._condition = QComboBox()
        self._condition.addItem("— select —", userData="")
        for key, cfg in load_conditions().items():
            label = cfg.get("label", key.title()) if isinstance(cfg, dict) else key.title()
            self._condition.addItem(label, userData=key)
        self._sku = QLineEdit()
        self._upc = QLineEdit()
        self._upc.setMaxLength(13)
        self._upc.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{0,13}"))
        )

        self._price = QDoubleSpinBox()
        self._price.setRange(0, 9_999_999.99)
        self._price.setDecimals(2)
        self._price.setPrefix("$ ")

        core = QFormLayout()
        core.setSpacing(4)
        core.setVerticalSpacing(4)
        core.addRow("Category", self._category)
        core.addRow("Manufacturer", self._manufacturer)
        core.addRow("MPN", self._mpn)
        core.addRow("Conditon", self._condition)
        core.addRow("SKU", self._sku)
        core.addRow("UPC", self._upc)
        core.addRow("Price", self._price)

        self._newegg_box = QGroupBox("Newegg")
        self._newegg_box.setCheckable(True)
        self._newegg_box.setChecked(True)
        self._newegg_shipping = QComboBox()
        self._newegg_shipping.addItems(["Free", "Default"])
        self._newegg_upc = QLineEdit()
        self._newegg_upc.setMaxLength(13)
        self._newegg_upc.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{0,13}"))
        )
        ne_form = QFormLayout()
        ne_form.setSpacing(4)
        ne_form.addRow("Shipping", self._newegg_shipping)
        ne_form.addRow("UPC", self._newegg_upc)
        self._newegg_box.setLayout(ne_form)

        self._bestbuy_box = QGroupBox("Best Buy")
        self._bestbuy_box.setCheckable(True)
        self._bestbuy_box.setChecked(True)
        self._bb_size = QComboBox()
        self._bb_size.addItem("— select —", userData="")
        for size in ["LETTER", "MED", "LARGE"]:
            self._bb_size.addItem(size, userData=size)
        self._bb_size.setCurrentIndex(0)
        self._bb_list = QDoubleSpinBox()
        self._bb_list.setRange(0, 9_999_999.99)
        self._bb_list.setDecimals(2)
        self._bb_list.setPrefix("$ ")
        self._bb_discount = QDoubleSpinBox()
        self._bb_discount.setRange(0, 9_999_999.99)
        self._bb_discount.setDecimals(2)
        self._bb_discount.setPrefix("$ ")
        self._bb_discount.setReadOnly(True)
        self._ehf = QComboBox()
        self._ehf.addItem("— select —", userData="")
        for key in ehf_profiles:
            self._ehf.addItem(str(key), userData=key)
        self._ehf.setCurrentIndex(0)
        self._bb_upc = QLineEdit()
        self._bb_upc.setMaxLength(13)
        self._bb_upc.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{0,13}"))
        )

        bb_form = QFormLayout()
        bb_form.setSpacing(4)
        bb_form.addRow("Package size", self._bb_size)
        bb_form.addRow("List price", self._bb_list)
        bb_form.addRow("Discount", self._bb_discount)
        bb_form.addRow("EHF profile", self._ehf)
        bb_form.addRow("UPC", self._bb_upc)
        self._bestbuy_box.setLayout(bb_form)

        remove_btn = QPushButton("Remove")
        remove_btn.setMaximumHeight(26)
        remove_btn.clicked.connect(lambda: self.removed.emit(self))

        self._title_label = QLineEdit()
        self._title_label.setReadOnly(True)
        self._title_label.setFrame(False)
        self._title_label.setStyleSheet(
            "font-size: 12px; font-weight: 600; background: transparent; border: none;"
        )
        self._toggle_btn = QPushButton("[-]")
        self._toggle_btn.setFixedSize(28, 24)
        self._toggle_btn.setToolTip("Collapse / expand item")
        self._toggle_btn.clicked.connect(self._toggle_expanded)

        header = QHBoxLayout()
        header.addWidget(self._title_label)
        header.addStretch()
        header.addWidget(self._toggle_btn)

        marketplaces = QHBoxLayout()
        marketplaces.setSpacing(8)
        marketplaces.addWidget(self._newegg_box, 1)
        marketplaces.addWidget(self._bestbuy_box, 1)

        self._content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(8)
        content_layout.addLayout(core)
        content_layout.addLayout(marketplaces)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(remove_btn)
        content_layout.addLayout(actions)
        self._content.setLayout(content_layout)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self._content)
        self.setLayout(layout)

        self._mpn.textChanged.connect(self._on_mpn)
        self._category.currentIndexChanged.connect(self._update_sku)
        self._price.valueChanged.connect(self._sync_bb_prices)
        self._upc.textChanged.connect(self._sync_marketplace_upc)
        self._condition.currentIndexChanged.connect(self._update_sku)
        self._sync_bb_prices()
        self._refresh_title()

    def _category_value(self) -> str:
        data = self._category.currentData()
        if data:
            return str(data)
        return ""
    def _manufacturer_value(self) -> str:
        data = self._manufacturer.currentData()
        if data or str(data) != "— select —":
            return str(data)
        return self._manufacturer.currentText().strip()

    def _condition_value(self) -> str:
        data = self._condition.currentData()
        if data or str(data) != "— select —":
            return str(data)
        return self._condition.currentText().strip()

    def _sync_marketplace_upc(self) -> None:
        upc = self._upc.text().strip()
        self._newegg_upc.setText(upc)
        self._bb_upc.setText(upc)

    def _toggle_expanded(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._toggle_btn.setText("[-]" if self._expanded else "[+]")

    def _refresh_title(self) -> None:
        sku = self._sku.text().strip().upper()
        self._title_label.setText(f"Item {self._index} — {sku or '—'}")

    def _on_mpn(self, text: str) -> None:
        upper = text.upper()
        if text != upper:
            self._mpn.blockSignals(True)
            self._mpn.setText(upper)
            self._mpn.blockSignals(False)
        self._update_sku()
        self.changed.emit()


    def _update_sku(self) -> None:
        mpn = self._mpn.text().strip().upper()
        if not mpn:
            self._sku.clear()
            self._refresh_title()
            return

        category_key = self._category.currentData()
        code = sku_prefix(category_key)

        condition_key = self._condition.currentData()
        conditions = load_conditions()
        suffix_list = (conditions.get(condition_key) or {}).get("suffix", [""])
        suffix = suffix_list[0] if suffix_list else ""

        sku = f"{code}-{mpn}{suffix}"

        self._sku.setText(sku)
        self._refresh_title()


    def _sync_bb_prices(self) -> None:
        discount = round(self._price.value(), 2)
        self._bb_discount.setValue(discount)
        self._bb_list.setValue(bestbuy_list_price_from_discount(discount))

    def validation_errors_scrape(self) -> list[str]:
        errors: list[str] = []
        label = f"Item {self._index}"
        if not self._category_value():
            errors.append(f"{label}: select Category")
        if not self._manufacturer_value():
            errors.append(f"{label}: select Manufacturer")
        if not self._mpn.text().strip():
            errors.append(f"{label}: enter MPN")
        if not self._condition_value():
            errors.append(f"{label}: select Condition")
        return errors

    def validation_errors_export(self) -> list[str]:
        errors = self.validation_errors_scrape()
        label = f"Item {self._index}"
        if self._bestbuy_box.isChecked():
            if not self._ehf.currentData():
                errors.append(f"{label}: select EHF profile (Best Buy)")
            if not self._bb_size.currentData():
                errors.append(f"{label}: select package size (Best Buy)")
        return errors

    def to_job(self) -> dict | None:
        if self.validation_errors_scrape():
            return None
        category_key = self._category.currentData()
        return {
            "mpn": self._mpn.text().strip().upper(),
            "product_code": product_code(category_key),
            "submission": self.to_submission(),
        }

    def to_submission(self) -> dict:
        category_key = self._category.currentData()
        discount = round(self._price.value(), 2)
        list_price = bestbuy_list_price_from_discount(discount)
        discount_start, discount_end = bestbuy_discount_dates()
        main_upc = self._upc.text().strip()
        newegg_upc = self._newegg_upc.text().strip() or main_upc
        bb_upc = self._bb_upc.text().strip() or main_upc

        return {
            "category": category_key,
            "manufacturer": self._manufacturer_value(),
            "price": discount,
            "condition": self._condition_value(),
            "sku": self._sku.text().strip(),
            "upc": bb_upc,
            "marketplaces": {
                "newegg": {
                    "enabled": self._newegg_box.isChecked(),
                    "condition": self._condition_value(),
                    "shipping_type": self._newegg_shipping.currentText(),
                    "category_path": marketplace_code(category_key, "newegg"),
                    "upc": newegg_upc,
                },
                "bestbuy": {
                    "enabled": self._bestbuy_box.isChecked(),
                    # "open_box": self._open_box.isChecked(),
                    "condition": self._condition_value(),
                    "package_size": self._bb_size.currentData() or "",
                    "list_price": list_price,
                    "discount_price": discount,
                    "discount_start_date": discount_start,
                    "discount_end_date": discount_end,
                    "ehf_profile": self._ehf.currentData() or "",
                    "upc": bb_upc,
                },
            },
        }
