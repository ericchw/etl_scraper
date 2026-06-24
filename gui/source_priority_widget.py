"""Drag-and-drop source priority cards (spec / packing / photo / features / design)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.merge_policy import (
    load_merge_sources,
    save_merge_sources,
)


class DragListWidget(QListWidget):
    def __init__(self) -> None:
        super().__init__()

        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(False)

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )

        self.setDefaultDropAction(
            Qt.DropAction.MoveAction
        )

        self.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        self.setFixedHeight(82)
        self.setSpacing(8)

        self.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 8px;
                background: #202124;
            }

            QListWidget::item {
                border: 1px solid #4a4a4a;
                border-radius: 8px;
                padding: 10px 16px;
                margin: 2px;
                background: #2b2d31;
                min-width: 120px;
                max-width: 180px;
            }

            QListWidget::item:selected {
                background: #3b82f6;
                color: white;
            }
            """
        )


class SourcePriorityWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._spec = DragListWidget()
        self._packing = DragListWidget()
        self._photo = DragListWidget()
        self._features = DragListWidget()
        self._design = DragListWidget()

        columns = QVBoxLayout()
        columns.setSpacing(14)

        columns.addWidget(
            self._build_box(
                "Spec",
                "Structured internal schema (processor, memory, display, …)",
                self._spec,
            )
        )

        columns.addWidget(
            self._build_box(
                "Packing",
                "Package dimensions & weight",
                self._packing,
            )
        )

        columns.addWidget(
            self._build_box(
                "Photo",
                "Image URLs — first source only (no merge)",
                self._photo,
            )
        )

        columns.addWidget(
            self._build_box(
                "Features",
                "Bullet list → BB short / Newegg Bullet Description",
                self._features,
            )
        )

        columns.addWidget(
            self._build_box(
                "Design",
                "Prose description → long description body (before specs)",
                self._design,
            )
        )

        hint = QLabel(
            "Drag cards horizontally to reorder. Left = highest priority."
        )

        hint.setStyleSheet(
            "color: #9aa0a6; font-size: 12px;"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        root.addWidget(hint)
        root.addLayout(columns)

        self.reload()

    def _build_box(
        self,
        title: str,
        subtitle: str,
        lst: QListWidget,
    ) -> QGroupBox:
        box = QGroupBox(title)

        sub = QLabel(subtitle)
        sub.setWordWrap(True)

        sub.setStyleSheet(
            "color: #9aa0a6; font-size: 11px;"
        )

        layout = QVBoxLayout()
        layout.setSpacing(8)

        layout.addWidget(sub)
        layout.addWidget(lst)

        box.setLayout(layout)

        return box

    def reload(self) -> None:
        cfg = load_merge_sources()

        self._fill(self._spec, cfg.get("spec") or [])
        self._fill(self._packing, cfg.get("packing") or [])
        self._fill(self._photo, cfg.get("photo") or [])
        self._fill(self._features, cfg.get("features") or [])
        self._fill(self._design, cfg.get("design") or [])

    def _fill(
        self,
        lst: QListWidget,
        names: list[str],
    ) -> None:
        lst.clear()

        for name in names:
            item = QListWidgetItem(f"☰  {name}")
            lst.addItem(item)

    def save(self) -> None:
        spec = [
            self._clean(self._spec.item(i).text())
            for i in range(self._spec.count())
        ]

        packing = [
            self._clean(self._packing.item(i).text())
            for i in range(self._packing.count())
        ]

        photo = [
            self._clean(self._photo.item(i).text())
            for i in range(self._photo.count())
        ]

        features = [
            self._clean(self._features.item(i).text())
            for i in range(self._features.count())
        ]

        design = [
            self._clean(self._design.item(i).text())
            for i in range(self._design.count())
        ]

        save_merge_sources(
            spec,
            packing,
            photo,
            features,
            design,
        )

    def _clean(self, text: str) -> str:
        return text.replace("☰", "").strip()
