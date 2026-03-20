from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from PyQt6.QtCore import Qt

from ea_node_editor.custom_workflows import (
    CUSTOM_WORKFLOW_FILE_EXTENSION,
    export_custom_workflow_file,
    import_custom_workflow_file,
)
from ea_node_editor.settings import plugins_dir

if TYPE_CHECKING:
    from ea_node_editor.nodes.package_manager import PackageExportSource
    from ea_node_editor.nodes.types import PluginDescriptor, PluginProvenance
    from ea_node_editor.ui.shell.window import ShellWindow


class _WorkspaceIOControllerProtocol(Protocol):
    def _custom_workflow_definitions(self) -> list[dict[str, Any]]: ...

    def _set_custom_workflow_definitions(self, definitions: list[dict[str, Any]]) -> None: ...

    def _prompt_custom_workflow_export_definition(
        self,
        definitions: list[dict[str, Any]],
    ) -> dict[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class _NodePackageImportOutcome:
    declared_node_ids: tuple[str, ...]
    loaded_node_ids: tuple[str, ...]
    available_node_ids: tuple[str, ...]
    missing_node_ids: tuple[str, ...]

    @property
    def approved_no_node_outcome(self) -> bool:
        return not self.declared_node_ids

    @property
    def newly_available_node_ids(self) -> tuple[str, ...]:
        loaded = set(self.loaded_node_ids)
        return tuple(node_id for node_id in self.available_node_ids if node_id in loaded)

    @property
    def already_available_node_ids(self) -> tuple[str, ...]:
        loaded = set(self.loaded_node_ids)
        return tuple(node_id for node_id in self.available_node_ids if node_id not in loaded)


@dataclass(frozen=True, slots=True)
class _NodePackageExportCandidate:
    package_name: str
    source_kind: str
    node_type_ids: tuple[str, ...]
    source_files: tuple[PackageExportSource, ...]
    descriptors: tuple[PluginDescriptor, ...]
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    dependencies: tuple[str, ...] = ()


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

    @staticmethod
    def _normalized_node_type_ids(node_ids: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_node_id in node_ids:
            node_id = str(raw_node_id).strip()
            if not node_id or node_id in seen:
                continue
            seen.add(node_id)
            normalized.append(node_id)
        return tuple(normalized)

    def _node_package_import_outcome(
        self,
        manifest_node_ids: list[str],
        loaded_type_ids: list[str],
    ) -> _NodePackageImportOutcome:
        declared_node_ids = self._normalized_node_type_ids(manifest_node_ids)
        loaded_node_ids = self._normalized_node_type_ids(loaded_type_ids)
        if not declared_node_ids:
            return _NodePackageImportOutcome(
                declared_node_ids=(),
                loaded_node_ids=loaded_node_ids,
                available_node_ids=(),
                missing_node_ids=(),
            )

        available_node_ids = tuple(
            node_id
            for node_id in declared_node_ids
            if self._host.registry.spec_or_none(node_id) is not None
        )
        available_node_id_set = set(available_node_ids)
        missing_node_ids = tuple(
            node_id for node_id in declared_node_ids if node_id not in available_node_id_set
        )
        return _NodePackageImportOutcome(
            declared_node_ids=declared_node_ids,
            loaded_node_ids=loaded_node_ids,
            available_node_ids=available_node_ids,
            missing_node_ids=missing_node_ids,
        )

    @staticmethod
    def _existing_package_metadata(source_dir: Path, fallback_name: str) -> dict[str, Any]:
        manifest_path = source_dir / "node_package.json"
        metadata: dict[str, Any] = {
            "name": fallback_name,
            "version": "1.0.0",
            "author": "",
            "description": "",
            "dependencies": (),
        }
        if not manifest_path.is_file():
            return metadata
        try:
            raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return metadata
        if isinstance(raw_manifest, dict):
            name = str(raw_manifest.get("name", fallback_name)).strip()
            metadata["name"] = name or fallback_name
            metadata["version"] = str(raw_manifest.get("version", "1.0.0"))
            metadata["author"] = str(raw_manifest.get("author", ""))
            metadata["description"] = str(raw_manifest.get("description", ""))
            metadata["dependencies"] = tuple(str(item) for item in raw_manifest.get("dependencies", []))
        return metadata

    @staticmethod
    def _descriptor_export_source(
        provenance: PluginProvenance | None,
        plugin_root: Path,
    ) -> tuple[tuple[str, str], tuple[PackageExportSource, ...], dict[str, Any]] | None:
        from ea_node_editor.nodes.package_manager import PackageExportSource

        if provenance is None:
            return None

        if provenance.kind == "file":
            source_path = provenance.source_path
            if source_path is None:
                return None
            source_path = source_path.resolve()
            try:
                relative_path = source_path.relative_to(plugin_root)
            except ValueError:
                return None
            if len(relative_path.parts) != 1:
                return None
            return (
                ("file", relative_path.name),
                (PackageExportSource(source_path=source_path, archive_name=relative_path.name),),
                {
                    "name": source_path.stem,
                    "version": "1.0.0",
                    "author": "",
                    "description": "",
                    "dependencies": (),
                },
            )

        if provenance.kind != "package":
            return None

        package_dir = provenance.package_root
        if package_dir is None:
            source_path = provenance.source_path
            if source_path is None:
                return None
            package_dir = source_path.parent
        package_dir = package_dir.resolve()
        try:
            relative_path = package_dir.relative_to(plugin_root)
        except ValueError:
            return None
        if len(relative_path.parts) != 1:
            return None

        source_files = tuple(
            PackageExportSource(source_path=source_path, archive_name=source_path.name)
            for source_path in sorted(package_dir.glob("*.py"))
            if source_path.is_file()
        )
        if not source_files:
            return None
        fallback_name = provenance.package_name or relative_path.parts[0]
        metadata = WorkspaceIOOps._existing_package_metadata(package_dir, fallback_name)
        return (("package", relative_path.parts[0]), source_files, metadata)

    @staticmethod
    def collect_node_package_export_candidates(
        registry: Any,
        plugin_root: Path,
    ) -> list[_NodePackageExportCandidate]:
        from ea_node_editor.nodes.package_manager import PackageExportSource

        builders: dict[tuple[str, str], dict[str, Any]] = {}
        plugin_root = plugin_root.resolve()
        descriptors = tuple(registry.all_descriptors())
        for descriptor in descriptors:
            export_source = WorkspaceIOOps._descriptor_export_source(
                descriptor.provenance,
                plugin_root,
            )
            if export_source is None:
                continue
            key, source_files, metadata = export_source

            builder = builders.setdefault(
                key,
                {
                    "package_name": metadata["name"],
                    "source_kind": key[0],
                    "source_files": source_files,
                    "node_type_ids": [],
                    "descriptors": [],
                    "version": metadata["version"],
                    "author": metadata["author"],
                    "description": metadata["description"],
                    "dependencies": metadata["dependencies"],
                },
            )
            builder["node_type_ids"].append(descriptor.spec.type_id)
            builder["descriptors"].append(descriptor)

        candidates = [
            _NodePackageExportCandidate(
                package_name=str(builder["package_name"]),
                source_kind=str(builder["source_kind"]),
                node_type_ids=WorkspaceIOOps._normalized_node_type_ids(builder["node_type_ids"]),
                source_files=tuple(builder["source_files"]),
                descriptors=tuple(builder["descriptors"]),
                version=str(builder["version"]),
                author=str(builder["author"]),
                description=str(builder["description"]),
                dependencies=tuple(str(item) for item in builder["dependencies"]),
            )
            for builder in builders.values()
            if builder["source_files"] and builder["node_type_ids"] and builder["descriptors"]
        ]
        candidates.sort(key=lambda candidate: (candidate.package_name.lower(), candidate.source_kind))
        return candidates

    @staticmethod
    def node_package_export_label(candidate: _NodePackageExportCandidate) -> str:
        node_count = len(candidate.node_type_ids)
        node_label = "node" if node_count == 1 else "nodes"
        source_kind = "package" if candidate.source_kind == "package" else "single file"
        return f"{candidate.package_name} ({node_count} {node_label}, {source_kind})"

    def prompt_node_package_export_candidate(
        self,
        candidates: list[_NodePackageExportCandidate],
    ) -> _NodePackageExportCandidate | None:
        from PyQt6.QtWidgets import QInputDialog

        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        labels = [self.node_package_export_label(candidate) for candidate in candidates]
        selected_label, ok = QInputDialog.getItem(
            self._host,
            "Export Node Package",
            "Package:",
            labels,
            0,
            False,
        )
        if not ok:
            return None
        try:
            selected_index = labels.index(selected_label)
        except ValueError:
            return None
        return candidates[selected_index]

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
            loaded_type_ids = discover_and_load_plugins(self._host.registry)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Import Failed", f"Could not import package.\n{exc}")
            return

        outcome = self._node_package_import_outcome(manifest.nodes, loaded_type_ids)
        if outcome.available_node_ids:
            self._host.node_library_changed.emit()

        if outcome.approved_no_node_outcome:
            QMessageBox.information(
                self._host,
                "Import Successful",
                f"Installed '{manifest.name}' v{manifest.version}.\n\n"
                "Package manifest declares no node types, so there are no Node Library entries to refresh.",
            )
            return

        if outcome.missing_node_ids:
            available_summary = ""
            if outcome.available_node_ids:
                available_summary = f"\n\nAvailable now: {', '.join(outcome.available_node_ids)}."
            QMessageBox.warning(
                self._host,
                "Import Incomplete",
                f"Installed '{manifest.name}' v{manifest.version}, but "
                f"{len(outcome.missing_node_ids)} of {len(outcome.declared_node_ids)} declared node(s) "
                f"are not currently available.{available_summary}\n\n"
                f"Missing: {', '.join(outcome.missing_node_ids)}.\n\n"
                "Restart the application if this package replaced node types that were already loaded.",
            )
            return

        if outcome.newly_available_node_ids and outcome.already_available_node_ids:
            availability_summary = (
                f"Newly loaded: {', '.join(outcome.newly_available_node_ids)}.\n\n"
                f"Already available: {', '.join(outcome.already_available_node_ids)}."
            )
        elif outcome.already_available_node_ids:
            availability_summary = (
                "The package's declared node types were already available in the current session "
                "and remain in the Node Library."
            )
        else:
            availability_summary = "The nodes are now available in the Node Library."
        QMessageBox.information(
            self._host,
            "Import Successful",
            f"Installed '{manifest.name}' v{manifest.version} with {len(outcome.available_node_ids)} node(s).\n\n"
            f"{availability_summary}",
        )

    def export_node_package(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox

        from ea_node_editor.nodes.package_manager import PackageManifest, export_package

        candidates = self.collect_node_package_export_candidates(self._host.registry, plugins_dir())
        if not candidates:
            QMessageBox.information(
                self._host,
                "Export Node Package",
                "No exportable node-package sources are currently available.\n\n"
                "Only nodes loaded from the user plugins directory can be exported from the shell.",
            )
            return

        selected_candidate = self.prompt_node_package_export_candidate(candidates)
        if selected_candidate is None:
            return

        name, ok = QInputDialog.getText(
            self._host,
            "Export Node Package",
            "Package name:",
            QLineEdit.EchoMode.Normal,
            selected_candidate.package_name,
        )
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getSaveFileName(
            self._host, "Export Node Package", f"{name.strip()}.eanp", "Node Package (*.eanp)"
        )
        if not path:
            return
        manifest = PackageManifest(
            name=name.strip(),
            version=selected_candidate.version,
            author=selected_candidate.author,
            description=selected_candidate.description,
            nodes=list(selected_candidate.node_type_ids),
            dependencies=list(selected_candidate.dependencies),
        )
        try:
            saved_path = export_package(
                list(selected_candidate.source_files),
                manifest,
                Path(path),
                descriptors=selected_candidate.descriptors,
            )
            QMessageBox.information(self._host, "Export Successful", f"Package saved to {saved_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Export Failed", f"Could not export package.\n{exc}")
