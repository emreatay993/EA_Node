from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from PyQt6.QtCore import Qt

from ea_node_editor.custom_workflows import (
    CUSTOM_WORKFLOW_FILE_EXTENSION,
    export_custom_workflow_file,
    import_custom_workflow_file,
)

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class _WorkspaceIOControllerProtocol(Protocol):
    def _custom_workflow_definitions(self) -> list[dict[str, Any]]: ...

    def _set_custom_workflow_definitions(self, definitions: list[dict[str, Any]]) -> None: ...

    def _prompt_custom_workflow_export_definition(
        self,
        definitions: list[dict[str, Any]],
    ) -> dict[str, Any] | None: ...


class WorkspaceIOOps:
    def __init__(
        self,
        host: ShellWindow,
        controller: _WorkspaceIOControllerProtocol,
    ) -> None:
        self._host = host
        self._controller = controller

    @staticmethod
    def custom_workflow_export_label(definition: dict[str, Any]) -> str:
        name = str(definition.get("name", "")).strip() or "Custom Workflow"
        revision = int(definition.get("revision", 1))
        return f"{name} (rev {revision})"

    @staticmethod
    def custom_workflow_default_filename(name: object) -> str:
        normalized_name = str(name).strip()
        if not normalized_name:
            normalized_name = "custom_workflow"
        invalid_chars = '<>:"/\\|?*'
        safe_name = "".join("_" if character in invalid_chars else character for character in normalized_name)
        safe_name = safe_name.strip().strip(".")
        if not safe_name:
            safe_name = "custom_workflow"
        return f"{safe_name}{CUSTOM_WORKFLOW_FILE_EXTENSION}"

    def import_custom_workflow(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        path, _ = QFileDialog.getOpenFileName(
            self._host,
            "Import Custom Workflow",
            "",
            "Custom Workflow (*.eawf)",
        )
        if not path:
            return
        try:
            imported_definition = import_custom_workflow_file(Path(path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Import Failed", f"Could not import custom workflow.\n{exc}")
            return

        definitions = self._controller._custom_workflow_definitions()
        workflow_id = imported_definition["workflow_id"]
        replaced_existing = False
        for index, definition in enumerate(definitions):
            if definition["workflow_id"] != workflow_id:
                continue
            definitions[index] = imported_definition
            replaced_existing = True
            break
        if not replaced_existing:
            definitions.append(imported_definition)

        self._controller._set_custom_workflow_definitions(definitions)
        self._host.project_meta_changed.emit()
        self._host.node_library_changed.emit()
        action = "Updated" if replaced_existing else "Imported"
        QMessageBox.information(
            self._host,
            "Import Successful",
            f"{action} custom workflow '{imported_definition['name']}' (rev {imported_definition['revision']}).",
        )

    def export_custom_workflow(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        definitions = sorted(
            self._controller._custom_workflow_definitions(),
            key=lambda definition: (
                str(definition.get("name", "")).lower(),
                str(definition.get("workflow_id", "")).lower(),
            ),
        )
        if not definitions:
            QMessageBox.information(self._host, "Export Custom Workflow", "No custom workflows are available to export.")
            return

        selected_definition = self._controller._prompt_custom_workflow_export_definition(definitions)
        if selected_definition is None:
            return
        default_name = self.custom_workflow_default_filename(selected_definition.get("name"))
        path, _ = QFileDialog.getSaveFileName(
            self._host,
            "Export Custom Workflow",
            default_name,
            "Custom Workflow (*.eawf)",
        )
        if not path:
            return
        try:
            saved_path = export_custom_workflow_file(selected_definition, Path(path))
            QMessageBox.information(self._host, "Export Successful", f"Custom workflow saved to {saved_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Export Failed", f"Could not export custom workflow.\n{exc}")

    def prompt_custom_workflow_export_definition(
        self,
        definitions: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        from PyQt6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QVBoxLayout,
        )

        if not definitions:
            return None
        if len(definitions) == 1:
            return definitions[0]

        dialog = QDialog(self._host)
        dialog.setWindowTitle("Export Custom Workflow")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Workflow:", dialog))

        list_widget = QListWidget(dialog)
        for index, definition in enumerate(definitions):
            item = QListWidgetItem(self.custom_workflow_export_label(definition))
            item.setData(Qt.ItemDataRole.UserRole, index)
            list_widget.addItem(item)
        list_widget.setCurrentRow(0)
        list_widget.itemDoubleClicked.connect(lambda _item: dialog.accept())
        layout.addWidget(list_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return None
        current_item = list_widget.currentItem()
        if current_item is None:
            return None
        try:
            selected_index = int(current_item.data(Qt.ItemDataRole.UserRole))
        except (TypeError, ValueError):
            return None
        if selected_index < 0 or selected_index >= len(definitions):
            return None
        return definitions[selected_index]

    def import_node_package(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        from ea_node_editor.nodes.package_manager import import_package
        from ea_node_editor.nodes.plugin_loader import discover_and_load_plugins

        path, _ = QFileDialog.getOpenFileName(
            self._host, "Import Node Package", "", "Node Package (*.eanp)"
        )
        if not path:
            return
        try:
            manifest = import_package(Path(path))
            discover_and_load_plugins(self._host.registry)
            self._host.node_library_changed.emit()
            QMessageBox.information(
                self._host,
                "Import Successful",
                f"Installed '{manifest.name}' v{manifest.version} "
                f"with {len(manifest.nodes)} node(s).\n\n"
                "The nodes are now available in the Node Library.",
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Import Failed", f"Could not import package.\n{exc}")

    def export_node_package(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

        from ea_node_editor.nodes.package_manager import PackageManifest, export_package

        name, ok = QInputDialog.getText(self._host, "Export Node Package", "Package name:")
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getSaveFileName(
            self._host, "Export Node Package", f"{name.strip()}.eanp", "Node Package (*.eanp)"
        )
        if not path:
            return
        manifest = PackageManifest(
            name=name.strip(),
            nodes=[spec.type_id for spec in self._host.registry.all_specs()],
        )
        try:
            export_package([], manifest, Path(path))
            QMessageBox.information(self._host, "Export Successful", f"Package saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Export Failed", f"Could not export package.\n{exc}")
