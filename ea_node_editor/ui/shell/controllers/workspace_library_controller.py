from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path

from PyQt6.QtCore import QRectF

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.graph.rules import find_port, is_port_exposed, ports_compatible
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.shell.inspector_flow import coerce_editor_input_value
from ea_node_editor.ui.shell.library_flow import input_port_is_available, pick_connection_candidate
from ea_node_editor.ui.shell.workspace_flow import build_workspace_tab_items, next_workspace_tab_index
from ea_node_editor.ui.shell.controllers.result import ControllerResult
from ea_node_editor.ui_qml.viewport_bridge import FRAME_PADDING_PX

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class WorkspaceLibraryController:
    def __init__(self, host: ShellWindow) -> None:
        self._host = host

    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None:
        node_id = self._host.scene.selected_node_id()
        if not node_id:
            return None
        workspace = self._host.model.project.workspaces.get(self._host.active_workspace_id)
        if workspace is None:
            return None
        node = workspace.nodes.get(node_id)
        if node is None:
            return None
        spec = self._host.registry.get_spec(node.type_id)
        return node, spec

    def set_selected_node_property(self, key: str, value: Any) -> None:
        selected = self.selected_node_context()
        if selected is None:
            return
        node, spec = selected
        property_spec = next((prop for prop in spec.properties if prop.key == key), None)
        if property_spec is None:
            return
        coerced = coerce_editor_input_value(property_spec.type, value, property_spec.default)
        self.on_node_property_changed(node.node_id, property_spec.key, coerced)

    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        selected = self.selected_node_context()
        if selected is None:
            return
        node, _spec = selected
        self.on_port_exposed_changed(node.node_id, str(key), bool(exposed))

    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        selected = self.selected_node_context()
        if selected is None:
            return
        node, spec = selected
        if not spec.collapsible:
            return
        self.on_node_collapse_changed(node.node_id, bool(collapsed))

    def switch_workspace_by_offset(self, offset: int) -> None:
        target = next_workspace_tab_index(
            self._host.workspace_tabs.count(),
            self._host.workspace_tabs.currentIndex(),
            offset,
        )
        if target is None:
            return
        self._host.workspace_tabs.setCurrentIndex(target)

    def refresh_workspace_tabs(self) -> None:
        current_workspace = self._host.workspace_manager.active_workspace_id()
        tabs = build_workspace_tab_items(self._host.workspace_manager.list_workspaces())
        self._host.workspace_tabs.set_tabs(tabs, current_workspace)
        self._host.workspace_state_changed.emit()

    def switch_workspace(self, workspace_id: str) -> None:
        self.save_active_view_state()
        if workspace_id not in self._host.model.project.workspaces:
            return
        self._host.workspace_manager.set_active_workspace(workspace_id)
        self._host.scene.set_workspace(self._host.model, self._host.registry, workspace_id)
        self.restore_active_view_state()
        self.refresh_workspace_tabs()
        self._host.script_editor.set_node(None)
        self._host.workspace_state_changed.emit()

    def save_active_view_state(self) -> None:
        if not self._host.scene.workspace_id:
            return
        workspace = self._host.model.project.workspaces.get(self._host.scene.workspace_id)
        if workspace is None:
            return
        workspace.ensure_default_view()
        view_state = workspace.views.get(workspace.active_view_id)
        if view_state is None:
            workspace.active_view_id = next(iter(workspace.views))
            view_state = workspace.views[workspace.active_view_id]
        view_state.zoom = self._host.view.zoom
        center = self._host.view.mapToScene(self._host.view.viewport().rect().center())
        view_state.pan_x = center.x()
        view_state.pan_y = center.y()

    def restore_active_view_state(self) -> None:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return
        workspace.ensure_default_view()
        view_state = workspace.views.get(workspace.active_view_id)
        if view_state is None:
            workspace.active_view_id = next(iter(workspace.views))
        view_state = workspace.views[workspace.active_view_id]
        self._host.view.set_zoom(max(0.1, min(3.0, view_state.zoom)))
        self._host.view.centerOn(view_state.pan_x, view_state.pan_y)

    def visible_scene_rect(self) -> QRectF:
        return self._host.view.visible_scene_rect()

    def current_workspace_scene_bounds(self) -> QRectF | None:
        return self._host.scene.workspace_scene_bounds()

    def selection_bounds(self) -> QRectF | None:
        return self._host.scene.selection_bounds()

    def frame_all(self) -> bool:
        return self._frame_scene_bounds(self.current_workspace_scene_bounds())

    def frame_selection(self) -> bool:
        return self._frame_scene_bounds(self.selection_bounds())

    def center_on_node(self, node_id: str) -> bool:
        bounds = self._host.scene.node_bounds(str(node_id).strip())
        if bounds is None:
            return False
        return self._host.view.center_on_scene_rect(bounds)

    def center_on_selection(self) -> bool:
        bounds = self.selection_bounds()
        if bounds is None:
            return False
        return self._host.view.center_on_scene_rect(bounds)

    def _frame_scene_bounds(self, bounds: QRectF | None) -> bool:
        if bounds is None:
            return False
        if bounds.width() <= 0.0 or bounds.height() <= 0.0:
            return False
        return self._host.view.frame_scene_rect(bounds, padding_px=FRAME_PADDING_PX)

    def create_view(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        workspace_id = self._host.workspace_manager.active_workspace_id()
        self.save_active_view_state()
        name, ok = QInputDialog.getText(self._host, "New View", "View name:")
        if not ok:
            return
        normalized_name = str(name).strip()
        view_id = self._host.workspace_manager.create_view(workspace_id, name=normalized_name or None)
        self._host.workspace_manager.set_active_view(workspace_id, view_id)
        self.restore_active_view_state()
        self._host.workspace_state_changed.emit()

    def switch_view(self, view_id: str) -> None:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        self.save_active_view_state()
        self._host.workspace_manager.set_active_view(workspace_id, view_id)
        self.restore_active_view_state()
        self._host.workspace_state_changed.emit()

    def create_workspace(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self._host, "New Workspace", "Workspace name:")
        if not ok:
            return
        workspace_id = self._host.workspace_manager.create_workspace(name=name or None)
        self.refresh_workspace_tabs()
        self.switch_workspace(workspace_id)

    def rename_active_workspace(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        index = self._host.workspace_tabs.currentIndex()
        if index < 0:
            return
        workspace_id = self._host.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        workspace = self._host.model.project.workspaces[workspace_id]
        name, ok = QInputDialog.getText(self._host, "Rename Workspace", "New name:", text=workspace.name)
        if ok and name.strip():
            self._host.workspace_manager.rename_workspace(workspace_id, name.strip())
            self.refresh_workspace_tabs()

    def duplicate_active_workspace(self) -> None:
        index = self._host.workspace_tabs.currentIndex()
        if index < 0:
            return
        workspace_id = self._host.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        duplicated_id = self._host.workspace_manager.duplicate_workspace(workspace_id)
        self.refresh_workspace_tabs()
        self.switch_workspace(duplicated_id)

    def close_active_workspace(self) -> None:
        index = self._host.workspace_tabs.currentIndex()
        if index >= 0:
            self.on_workspace_tab_close(index)

    def on_workspace_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        workspace_id = self._host.workspace_tabs.tabData(index)
        if workspace_id:
            self.switch_workspace(workspace_id)

    def on_workspace_tab_close(self, index: int) -> None:
        from PyQt6.QtWidgets import QMessageBox

        workspace_id = self._host.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        workspace = self._host.model.project.workspaces[workspace_id]
        if workspace.dirty:
            reply = QMessageBox.question(
                self._host,
                "Unsaved Changes",
                f"Workspace '{workspace.name}' has unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            self._host.workspace_manager.close_workspace(workspace_id)
        except ValueError:
            QMessageBox.warning(self._host, "Workspace", "Cannot close the last workspace.")
            return
        self.refresh_workspace_tabs()
        self.switch_workspace(self._host.workspace_manager.active_workspace_id())

    def add_node_from_library(self, type_id: str) -> None:
        center = self._host.view.mapToScene(self._host.view.viewport().rect().center())
        if self.insert_library_node(type_id, center.x(), center.y()):
            self.refresh_workspace_tabs()

    def insert_library_node(self, type_id: str, x: float, y: float) -> str:
        normalized_type = str(type_id).strip()
        if not normalized_type:
            return ""
        try:
            return self._host.scene.add_node_from_type(normalized_type, x=float(x), y=float(y))
        except (KeyError, RuntimeError, ValueError):
            return ""

    def active_workspace(self):
        workspace_id = self._host.workspace_manager.active_workspace_id()
        return self._host.model.project.workspaces.get(workspace_id)

    def prompt_connection_candidate(
        self,
        *,
        title: str,
        label: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return pick_connection_candidate(
            parent=self._host,
            title=title,
            label=label,
            candidates=candidates,
        )

    def auto_connect_dropped_node_to_port(
        self,
        new_node_id: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        workspace = self.active_workspace()
        if workspace is None:
            return False

        new_node = workspace.nodes.get(new_node_id)
        target_node = workspace.nodes.get(target_node_id)
        if new_node is None or target_node is None:
            return False

        new_spec = self._host.registry.get_spec(new_node.type_id)
        target_spec = self._host.registry.get_spec(target_node.type_id)
        target_port = find_port(target_spec, str(target_port_key).strip())
        if target_port is None:
            return False

        candidates: list[dict[str, Any]] = []
        if target_port.direction == "in":
            if not input_port_is_available(workspace, target_node.node_id, target_port.key):
                return False
            for port in new_spec.ports:
                if port.direction != "out" or not is_port_exposed(new_node, new_spec, port.key):
                    continue
                if not ports_compatible(port, target_port):
                    continue
                candidates.append(
                    {
                        "source_node_id": new_node.node_id,
                        "source_port_key": port.key,
                        "target_node_id": target_node.node_id,
                        "target_port_key": target_port.key,
                        "label": f"{new_spec.display_name}.{port.key} -> {target_spec.display_name}.{target_port.key}",
                    }
                )
        elif target_port.direction == "out":
            for port in new_spec.ports:
                if port.direction != "in" or not is_port_exposed(new_node, new_spec, port.key):
                    continue
                if not ports_compatible(target_port, port):
                    continue
                candidates.append(
                    {
                        "source_node_id": target_node.node_id,
                        "source_port_key": target_port.key,
                        "target_node_id": new_node.node_id,
                        "target_port_key": port.key,
                        "label": f"{target_spec.display_name}.{target_port.key} -> {new_spec.display_name}.{port.key}",
                    }
                )
        else:
            return False

        selected = self.prompt_connection_candidate(
            title="Auto-Connect Port",
            label="Choose connection:",
            candidates=candidates,
        )
        if selected is None:
            return False

        try:
            self._host.scene.add_edge(
                selected["source_node_id"],
                selected["source_port_key"],
                selected["target_node_id"],
                selected["target_port_key"],
            )
            return True
        except (KeyError, ValueError):
            return False

    def auto_connect_dropped_node_to_edge(self, new_node_id: str, target_edge_id: str) -> bool:
        workspace = self.active_workspace()
        if workspace is None:
            return False
        edge = workspace.edges.get(target_edge_id)
        new_node = workspace.nodes.get(new_node_id)
        if edge is None or new_node is None:
            return False

        source_node = workspace.nodes.get(edge.source_node_id)
        target_node = workspace.nodes.get(edge.target_node_id)
        if source_node is None or target_node is None:
            return False

        source_spec = self._host.registry.get_spec(source_node.type_id)
        target_spec = self._host.registry.get_spec(target_node.type_id)
        new_spec = self._host.registry.get_spec(new_node.type_id)
        source_port = find_port(source_spec, str(edge.source_port_key).strip())
        target_port = find_port(target_spec, str(edge.target_port_key).strip())
        if source_port is None or target_port is None:
            return False

        candidate_inputs = [
            port
            for port in new_spec.ports
            if port.direction == "in"
            and is_port_exposed(new_node, new_spec, port.key)
            and ports_compatible(source_port, port)
        ]
        candidate_outputs = [
            port
            for port in new_spec.ports
            if port.direction == "out"
            and is_port_exposed(new_node, new_spec, port.key)
            and ports_compatible(port, target_port)
        ]

        candidates: list[dict[str, Any]] = []
        for input_port in candidate_inputs:
            for output_port in candidate_outputs:
                candidates.append(
                    {
                        "new_input_port": input_port.key,
                        "new_output_port": output_port.key,
                        "label": (
                            f"{source_spec.display_name}.{source_port.key} -> {new_spec.display_name}.{input_port.key}, "
                            f"{new_spec.display_name}.{output_port.key} -> {target_spec.display_name}.{target_port.key}"
                        ),
                    }
                )

        selected = self.prompt_connection_candidate(
            title="Auto-Insert On Edge",
            label="Choose inserted wiring:",
            candidates=candidates,
        )
        if selected is None:
            return False

        original = {
            "source_node_id": edge.source_node_id,
            "source_port_key": edge.source_port_key,
            "target_node_id": edge.target_node_id,
            "target_port_key": edge.target_port_key,
        }
        created_edge_ids: list[str] = []
        removed_original = False
        try:
            self._host.scene.remove_edge(target_edge_id)
            removed_original = True
            first_id = self._host.scene.add_edge(
                original["source_node_id"],
                original["source_port_key"],
                new_node_id,
                selected["new_input_port"],
            )
            created_edge_ids.append(first_id)
            second_id = self._host.scene.add_edge(
                new_node_id,
                selected["new_output_port"],
                original["target_node_id"],
                original["target_port_key"],
            )
            created_edge_ids.append(second_id)
            return True
        except (KeyError, ValueError):
            for edge_id in created_edge_ids:
                self._host.scene.remove_edge(edge_id)
            if removed_original:
                try:
                    self._host.scene.add_edge(
                        original["source_node_id"],
                        original["source_port_key"],
                        original["target_node_id"],
                        original["target_port_key"],
                    )
                except (KeyError, ValueError):
                    pass
            return False

    def on_scene_node_selected(self, node_id: str) -> None:
        workspace = self._host.model.project.workspaces[self._host.workspace_manager.active_workspace_id()]
        node = workspace.nodes.get(node_id)
        self._host.script_editor.set_node(node)
        if self._host.script_editor.visible:
            self._host.script_editor.focus_editor()
        self._host.selected_node_changed.emit()

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None:
        self._host.scene.set_node_property(node_id, key, value)
        if key == "script" and self._host.script_editor.current_node_id == node_id:
            workspace = self._host.model.project.workspaces[self._host.workspace_manager.active_workspace_id()]
            self._host.script_editor.set_node(workspace.nodes.get(node_id))
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()

    def on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None:
        self._host.scene.set_exposed_port(node_id, key, exposed)
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None:
        self._host.scene.set_node_collapsed(node_id, collapsed)
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()

    def connect_selected_nodes(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        selected = [item for item in self._host.scene.selectedItems() if hasattr(item, "node")]
        if len(selected) != 2:
            QMessageBox.information(self._host, "Connect", "Select exactly two nodes to connect.")
            return
        first_item = selected[0]
        second_item = selected[1]
        try:
            self._host.scene.connect_nodes(first_item.node.node_id, second_item.node.node_id)
        except (KeyError, ValueError):
            QMessageBox.warning(self._host, "Connect", "No compatible ports found on selected nodes.")
            return
        self.refresh_workspace_tabs()

    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
    ) -> ControllerResult[bool]:
        created_node_id = self.insert_library_node(type_id, scene_x, scene_y)
        if not created_node_id:
            return ControllerResult(False, "Node could not be created.", payload=False)

        mode = str(target_mode).strip().lower()
        if mode == "port":
            self.auto_connect_dropped_node_to_port(
                created_node_id,
                str(target_node_id).strip(),
                str(target_port_key).strip(),
            )
        elif mode == "edge":
            self.auto_connect_dropped_node_to_edge(
                created_node_id,
                str(target_edge_id).strip(),
            )

        self.refresh_workspace_tabs()
        return ControllerResult(True, payload=True)

    def request_connect_ports(self, node_a_id: str, port_a: str, node_b_id: str, port_b: str) -> ControllerResult[bool]:
        result = self._host._graph_interactions.connect_ports(node_a_id, port_a, node_b_id, port_b)
        if result.ok:
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_remove_edge(self, edge_id: str) -> ControllerResult[bool]:
        result = self._host._graph_interactions.remove_edge(edge_id)
        if result.ok:
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_remove_node(self, node_id: str) -> ControllerResult[bool]:
        result = self._host._graph_interactions.remove_node(node_id)
        if result.ok:
            self._host.selected_node_changed.emit()
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_rename_node(self, node_id: str) -> ControllerResult[bool]:
        from PyQt6.QtWidgets import QInputDialog

        workspace = self._host.model.project.workspaces.get(self._host.workspace_manager.active_workspace_id())
        if workspace is None:
            return ControllerResult(False, payload=False)
        node = workspace.nodes.get(str(node_id).strip())
        if node is None:
            return ControllerResult(False, payload=False)
        new_title, ok = QInputDialog.getText(self._host, "Rename Node", "New name:", text=node.title)
        if not ok:
            return ControllerResult(False, payload=False)
        result = self._host._graph_interactions.rename_node(node.node_id, new_title)
        if result.ok:
            self._host.selected_node_changed.emit()
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> ControllerResult[bool]:
        result = self._host._graph_interactions.delete_selected_items(edge_ids)
        if result.ok:
            self._host.selected_node_changed.emit()
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None:
        from PyQt6.QtWidgets import QMessageBox

        if workspace_id and workspace_id != self._host.workspace_manager.active_workspace_id():
            self.switch_workspace(workspace_id)

        focus_candidates: list[str] = []
        if node_id:
            focus_candidates.append(node_id)
        focus_candidates.extend(self.reveal_parent_chain(workspace_id, node_id))

        focused_node_id = ""
        for target_node_id in focus_candidates:
            if self._host.scene.focus_node(target_node_id) is not None:
                focused_node_id = target_node_id
                break
        if focused_node_id:
            self.center_on_node(focused_node_id)
        if error:
            QMessageBox.critical(self._host, "Workflow Error", error)

    def reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]:
        if not workspace_id or not node_id:
            return []
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return []
        node = workspace.nodes.get(node_id)
        if node is None:
            return []

        chain: list[str] = []
        seen: set[str] = set()
        parent_id = node.parent_node_id
        while parent_id and parent_id not in seen:
            seen.add(parent_id)
            parent_node = workspace.nodes.get(parent_id)
            if parent_node is None:
                break
            chain.append(parent_id)
            parent_id = parent_node.parent_node_id

        for candidate_id in reversed(chain):
            parent_node = workspace.nodes.get(candidate_id)
            if parent_node is not None and parent_node.collapsed:
                self._host.scene.set_node_collapsed(candidate_id, False)
        return chain

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
