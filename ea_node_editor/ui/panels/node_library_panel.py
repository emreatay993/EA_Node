from __future__ import annotations

from collections import defaultdict

from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ea_node_editor.nodes.registry import NodeRegistry


class NodeLibraryPanel(QWidget):
    node_add_requested = pyqtSignal(str)

    def __init__(self, registry: NodeRegistry, parent=None) -> None:
        super().__init__(parent)
        self._registry = registry
        self._node_type_by_row: dict[int, str] = {}
        self._collapsed_categories: set[str] = set()

        title = QLabel("Node Library")
        title.setObjectName("panelTitle")

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search nodes...")

        self.category_combo = QComboBox()
        self.category_combo.addItem("All", "")

        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Any Port Direction", "")
        self.direction_combo.addItem("Input", "in")
        self.direction_combo.addItem("Output", "out")

        self.data_type_combo = QComboBox()
        self.data_type_combo.addItem("Any Data Type", "")

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        add_button = QPushButton("Add Selected")
        add_button.clicked.connect(self._on_add_clicked)

        form = QFormLayout()
        form.addRow("Category", self.category_combo)
        form.addRow("Port Dir", self.direction_combo)
        form.addRow("Port Type", self.data_type_combo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addWidget(self.search_edit)
        layout.addLayout(form)
        layout.addWidget(self.list_widget, stretch=1)
        layout.addWidget(add_button)

        self.search_edit.textChanged.connect(self.refresh)
        self.category_combo.currentIndexChanged.connect(self.refresh)
        self.direction_combo.currentIndexChanged.connect(self.refresh)
        self.data_type_combo.currentIndexChanged.connect(self.refresh)
        self._populate_filter_values()
        self.refresh()

    def _populate_filter_values(self) -> None:
        for category in self._registry.categories():
            self.category_combo.addItem(category, category)

        data_types = sorted({port.data_type for spec in self._registry.all_specs() for port in spec.ports})
        for data_type in data_types:
            self.data_type_combo.addItem(data_type, data_type)

    def refresh(self) -> None:
        query = self.search_edit.text()
        category = self.category_combo.currentData()
        data_type = self.data_type_combo.currentData()
        direction = self.direction_combo.currentData()
        specs = self._registry.filter_nodes(
            query=query,
            category=category or "",
            data_type=data_type or "",
            direction=direction or "",
        )

        grouped: dict[str, list] = defaultdict(list)
        for spec in specs:
            grouped[spec.category].append(spec)

        self.list_widget.clear()
        self._node_type_by_row.clear()

        row = 0
        for category in sorted(grouped):
            collapsed = category in self._collapsed_categories
            caret = "▶" if collapsed else "▼"
            header = QListWidgetItem(f"{caret} {category}")
            header.setData(Qt.ItemDataRole.UserRole, {"kind": "category", "category": category})
            header.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.list_widget.addItem(header)
            row += 1

            if collapsed:
                continue
            for spec in grouped[category]:
                label = f"[{spec.category}] {spec.display_name}"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, {"kind": "node", "type_id": spec.type_id})
                item.setToolTip(spec.description or spec.type_id)
                self.list_widget.addItem(item)
                self._node_type_by_row[row] = spec.type_id
                row += 1

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(payload, dict) and payload.get("kind") == "category":
            category = str(payload.get("category", "")).strip()
            if not category:
                return
            if category in self._collapsed_categories:
                self._collapsed_categories.remove(category)
            else:
                self._collapsed_categories.add(category)
            self.refresh()

    def _selected_type_id(self) -> str | None:
        row = self.list_widget.currentRow()
        if row >= 0:
            type_id = self._node_type_by_row.get(row)
            if type_id:
                return type_id

        current_item = self.list_widget.currentItem()
        if current_item is not None:
            current_row = self.list_widget.row(current_item)
            type_id = self._node_type_by_row.get(current_row)
            if type_id:
                return type_id

        selected_items = self.list_widget.selectedItems()
        if selected_items:
            selected_row = self.list_widget.row(selected_items[0])
            return self._node_type_by_row.get(selected_row)

        return None

    def _on_add_clicked(self) -> None:
        type_id = self._selected_type_id()
        if type_id:
            self.node_add_requested.emit(type_id)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:  # noqa: ARG002
        payload = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(payload, dict) and payload.get("kind") == "category":
            self._on_item_clicked(item)
            return
        type_id = self._selected_type_id()
        if type_id:
            self.node_add_requested.emit(type_id)
