"""Generate Best Buy / Newegg mapping YAML from template CSV."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.categories import load_categories
from core.yaml_generator import generate_all_missing, generate_mapping_yaml


class YamlGeneratorDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generate mapping YAML")
        self.setMinimumSize(560, 420)
        self.resize(640, 480)

        self._categories = load_categories()

        intro = QLabel(
            "Create scaffold YAML from template CSV headers. "
            "Existing mapping files are left unchanged unless you enable replace."
        )
        intro.setWordWrap(True)

        self._bestbuy_box = QCheckBox("Best Buy")
        self._bestbuy_box.setChecked(True)
        self._newegg_box = QCheckBox("Newegg")
        self._newegg_box.setChecked(True)

        market_row = QHBoxLayout()
        market_row.addWidget(self._bestbuy_box)
        market_row.addWidget(self._newegg_box)
        market_row.addStretch()

        self._category = QComboBox()
        for key, entry in self._categories.items():
            label = str(entry.get("label") or key)
            bb = entry.get("bestbuy") or "—"
            ne = entry.get("newegg") or "—"
            self._category.addItem(f"{label}  ({bb} / {ne})", key)

        self._replace_existing = QCheckBox("Replace existing YAML")
        self._replace_existing.setChecked(False)

        form = QFormLayout()
        form.addRow("Category", self._category)
        form.addRow("", self._replace_existing)

        self._generate_btn = QPushButton("Generate selected")
        self._generate_btn.clicked.connect(self._on_generate_selected)
        self._generate_all_btn = QPushButton("Generate all missing")
        self._generate_all_btn.clicked.connect(self._on_generate_all_missing)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._generate_btn)
        btn_row.addWidget(self._generate_all_btn)
        btn_row.addStretch()

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(160)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(market_row)
        layout.addLayout(form)
        layout.addLayout(btn_row)
        layout.addWidget(QLabel("Results"))
        layout.addWidget(self._log, stretch=1)
        layout.addWidget(buttons)

    def _append(self, line: str) -> None:
        self._log.append(line)

    def _selected_marketplaces(self) -> list[str]:
        marketplaces: list[str] = []
        if self._bestbuy_box.isChecked():
            marketplaces.append("bestbuy")
        if self._newegg_box.isChecked():
            marketplaces.append("newegg")
        return marketplaces

    def _confirm_replace(self) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Replace existing YAML?")
        box.setText("This will overwrite existing mapping files for the selected operation.")
        box.setInformativeText("Custom field rules in those files will be lost.")
        replace_btn = box.addButton("Replace", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is replace_btn

    def _run_generate(self, *, all_categories: bool) -> None:
        marketplaces = self._selected_marketplaces()
        if not marketplaces:
            QMessageBox.warning(self, "Generate YAML", "Select at least one marketplace.")
            return

        overwrite = self._replace_existing.isChecked()
        if overwrite and not self._confirm_replace():
            return

        self._log.clear()
        created = skipped = errors = 0

        if all_categories:
            for marketplace in marketplaces:
                self._append(f"=== {marketplace} (all categories) ===")
                for result in generate_all_missing(marketplace, overwrite=overwrite):
                    self._append(f"{result.category_key}: {result.status} — {result.message}")
                    if result.status == "created":
                        created += 1
                    elif result.status == "overwritten":
                        created += 1
                    elif result.status == "skipped_exists":
                        skipped += 1
                    else:
                        errors += 1
        else:
            category_key = self._category.currentData()
            for marketplace in marketplaces:
                result = generate_mapping_yaml(
                    category_key,
                    marketplace,
                    overwrite=overwrite,
                )
                self._append(f"{marketplace}/{category_key}: {result.status} — {result.message}")
                if result.status in {"created", "overwritten"}:
                    created += 1
                elif result.status == "skipped_exists":
                    skipped += 1
                else:
                    errors += 1

        self._append("")
        self._append(f"Done — created/overwritten: {created}, skipped: {skipped}, errors: {errors}")

    def _on_generate_selected(self) -> None:
        self._run_generate(all_categories=False)

    def _on_generate_all_missing(self) -> None:
        self._run_generate(all_categories=True)
