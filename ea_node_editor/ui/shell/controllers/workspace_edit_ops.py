from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from PyQt6.QtCore import QMimeData

from ea_node_editor.ui.shell.property_edit_adapters import (
    create_shell_property_edit_adapters,
)
from ea_node_editor.addons.property_edit_adapters import (
    PropertyEditAdapterContext,
    rewrite_property_edit_with_adapters,
)
from ea_node_editor.graph.effective_ports import (
    find_port as find_effective_port,
    is_subnode_pin_type,
)
from ea_node_editor.graph.hierarchy import scope_parent_id
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.builtins.media_panel import MEDIA_PANEL_TYPE_ID
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
    SUBNODE_PIN_KIND_PROPERTY,
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_TYPE_ID,
)
from ea_node_editor.ui.shell.controllers.dialog_support import resolve_dialog_parent
from ea_node_editor.ui.shell.controllers.mutation_ui_effects import MutationUiEffects
from ea_node_editor.ui.shell.controllers.result import ControllerResult
from ea_node_editor.ui.shell.clipboard_paste_nodes import (
    ClipboardPasteItem,
    ClipboardTablePasteItems,
    classify_clipboard_paste_items,
    clipboard_paste_items_signature,
    clipboard_table_paste_items,
)
from ea_node_editor.ui.shell.inspector_flow import coerce_editor_input_value
from ea_node_editor.ui.shell.runtime_clipboard import (
    GRAPH_FRAGMENT_MIME_TYPE,
    parse_graph_fragment_payload,
    serialize_graph_fragment_payload,
)
from ea_node_editor.ui.shell.runtime_history import HistoryEntry

if TYPE_CHECKING:
    from ea_node_editor.nodes.node_specs import NodeTypeSpec
    from ea_node_editor.ui.shell.window import ShellWindow

_PASTE_CASCADE_OFFSET_X = 40.0
_PASTE_CASCADE_OFFSET_Y = 40.0
_PIN_REFRESH_PROPERTIES = {
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_PIN_KIND_PROPERTY,
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
}


class _WorkspaceEditControllerProtocol(Protocol):
    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None: ...

    def active_workspace(self): ...

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None: ...

    def on_port_exposed_changed(
        self, node_id: str, key: str, exposed: bool
    ) -> None: ...

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None: ...

    def _write_graph_fragment_to_clipboard(
        self, fragment_payload: dict[str, Any]
    ) -> bool: ...

    def _read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None: ...

    def copy_selected_nodes_to_clipboard(self) -> bool: ...

    def request_delete_selected_graph_items(
        self, edge_ids: list[Any]
    ) -> ControllerResult[bool]: ...

    def clipboard_fragment_signature(self) -> str: ...

    def set_clipboard_fragment_signature(self, signature: str) -> None: ...

    def clipboard_paste_count(self) -> int: ...

    def set_clipboard_paste_count(self, count: int) -> None: ...

    def retarget_fragment_roots(
        self,
        fragment_payload: dict[str, Any],
        *,
        target_parent_id: str | None,
    ) -> dict[str, Any]: ...


class WorkspaceEditOps:
    def __init__(
        self,
        host: ShellWindow,
        controller: _WorkspaceEditControllerProtocol,
        effects: MutationUiEffects | None = None,
    ) -> None:
        self._host = host
        self._controller = controller
        self._effects = effects or MutationUiEffects(
            host=host,
            refresh_workspace_tabs=lambda: getattr(
                controller, "refresh_workspace_tabs", lambda: None
            )(),
        )

    @property
    def _graph_interactions(self):
        graph_interactions = getattr(self._host, "graph_interactions", None)
        if graph_interactions is not None:
            return graph_interactions
        return self._host._graph_interactions

    def set_selected_node_property(self, key: str, value: Any) -> None:
        selected = self._controller.selected_node_context()
        if selected is None:
            return
        node, spec = selected
        workspace = self._controller.active_workspace()
        rewrite = rewrite_property_edit_with_adapters(
            self._property_edit_adapters(),
            PropertyEditAdapterContext(
                node=node,
                spec=spec,
                workspace_nodes=workspace.nodes if workspace is not None else None,
                workspace_edges=workspace.edges if workspace is not None else None,
                project_path=str(getattr(self._host, "project_path", "") or "").strip()
                or None,
                project_metadata=self._project_metadata(),
            ),
            key=str(key or "").strip(),
            value=value,
        )
        if rewrite is not None:
            self._controller.on_node_property_changed(
                node.node_id, rewrite.key, rewrite.value
            )
            return
        property_spec = next(
            (prop for prop in spec.properties if prop.key == key), None
        )
        if property_spec is None:
            return
        coerced = coerce_editor_input_value(
            property_spec.type, value, property_spec.default
        )
        self._controller.on_node_property_changed(
            node.node_id, property_spec.key, coerced
        )

    def _preferences_document(self) -> dict[str, Any] | None:
        controller = getattr(self._host, "app_preferences_controller", None)
        document = getattr(controller, "document", None)
        if not callable(document):
            return None
        return document()

    def _property_edit_adapters(self) -> tuple[Any, ...]:
        return create_shell_property_edit_adapters(
            preferences_document=self._preferences_document(),
        )

    def _project_metadata(self) -> dict[str, Any] | None:
        project = getattr(getattr(self._host, "model", None), "project", None)
        metadata = getattr(project, "metadata", None)
        return dict(metadata) if isinstance(metadata, dict) else None

    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        selected = self._controller.selected_node_context()
        if selected is None:
            return
        node, spec = selected
        workspace = self._controller.active_workspace()
        if workspace is None:
            return
        normalized_key = str(key or "").strip()
        if not normalized_key:
            return
        port = find_effective_port(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
            port_key=normalized_key,
        )
        if port is None:
            return
        normalized_exposed = bool(exposed)
        if port.required and not normalized_exposed:
            return
        self._controller.on_port_exposed_changed(
            node.node_id, normalized_key, normalized_exposed
        )

    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        selected = self._controller.selected_node_context()
        if selected is None:
            return
        node, spec = selected
        if not spec.collapsible:
            return
        self._controller.on_node_collapse_changed(node.node_id, bool(collapsed))

    def request_add_selected_subnode_pin(self, direction: str) -> ControllerResult[str]:
        selected = self._controller.selected_node_context()
        if selected is None:
            return ControllerResult(False, "No node selected.", payload="")
        node, _spec = selected
        if node.type_id != SUBNODE_TYPE_ID:
            return ControllerResult(
                False, "Selected node is not a subnode shell.", payload=""
            )

        normalized_direction = str(direction).strip().lower()
        if normalized_direction == "in":
            pin_type_id = SUBNODE_INPUT_TYPE_ID
        elif normalized_direction == "out":
            pin_type_id = SUBNODE_OUTPUT_TYPE_ID
        else:
            return ControllerResult(
                False, "Unknown subnode port direction.", payload=""
            )

        created_node_id = self._host.scene.add_subnode_shell_pin(
            node.node_id, pin_type_id
        )
        if not created_node_id:
            return ControllerResult(
                False, "Subnode port could not be created.", payload=""
            )
        self._effects.after_subnode_pin_added()
        return ControllerResult(True, payload=created_node_id)

    def _selected_shell_pin_node(self, key: str) -> NodeInstance | None:
        selected = self._controller.selected_node_context()
        if selected is None:
            return None
        node, _spec = selected
        if node.type_id != SUBNODE_TYPE_ID:
            return None

        workspace = self._controller.active_workspace()
        if workspace is None:
            return None

        port_node_id = str(key or "").strip()
        if not port_node_id:
            return None
        pin_node = workspace.nodes.get(port_node_id)
        if pin_node is None or not self._is_direct_child_pin_node(
            pin_node, workspace.nodes
        ):
            return None
        if str(pin_node.parent_node_id or "").strip() != str(node.node_id):
            return None
        return pin_node

    def set_selected_port_label(self, key: str, label: Any) -> bool:
        pin_node = self._selected_shell_pin_node(key)
        if pin_node is not None:
            normalized_label = str(label or "").strip()
            if not normalized_label:
                return False
            current_label = str(
                pin_node.properties.get(SUBNODE_PIN_LABEL_PROPERTY, "")
            ).strip()
            if not current_label:
                current_label = (
                    "Input" if pin_node.type_id == SUBNODE_INPUT_TYPE_ID else "Output"
                )
            if normalized_label == current_label:
                return False
            self.on_node_property_changed(
                pin_node.node_id, SUBNODE_PIN_LABEL_PROPERTY, normalized_label
            )
            return True

        context = self._controller.selected_node_context()
        if context is None:
            return False
        node, spec = context
        port_key = str(key or "").strip()
        if not port_key:
            return False
        port_spec = next((p for p in spec.ports if p.key == port_key), None)
        if port_spec is None:
            return False
        normalized_label = str(label or "").strip()
        default_label = port_spec.label or port_spec.key
        current_label = node.port_labels.get(port_key) or default_label
        if normalized_label == current_label:
            return False
        store_label = "" if normalized_label == default_label else normalized_label
        workspace = self._controller.active_workspace()
        if workspace is None:
            return False
        self._host.scene.set_port_label(
            workspace.workspace_id, node.node_id, port_key, store_label
        )
        self._effects.after_selected_port_label_changed()
        return True

    def request_rename_selected_port(self, key: str) -> ControllerResult[bool]:
        from PyQt6.QtWidgets import QInputDialog

        pin_node = self._selected_shell_pin_node(key)
        if pin_node is None:
            return ControllerResult(False, "Subnode port not found.", payload=False)

        current_label = str(
            pin_node.properties.get(SUBNODE_PIN_LABEL_PROPERTY, "")
        ).strip()
        if not current_label:
            current_label = (
                "Input" if pin_node.type_id == SUBNODE_INPUT_TYPE_ID else "Output"
            )
        new_label, ok = QInputDialog.getText(
            resolve_dialog_parent(self._host),
            "Rename Port",
            "Port name:",
            text=current_label,
        )
        if not ok:
            return ControllerResult(False, payload=False)

        renamed = self.set_selected_port_label(key, new_label)
        if not renamed:
            normalized_label = str(new_label).strip()
            if not normalized_label:
                return ControllerResult(
                    False, "Port name cannot be empty.", payload=False
                )
            return ControllerResult(False, payload=False)
        return ControllerResult(True, payload=True)

    def request_remove_selected_port(self, key: str) -> ControllerResult[bool]:
        pin_node = self._selected_shell_pin_node(key)
        if pin_node is None:
            return ControllerResult(False, "Subnode port not found.", payload=False)

        removed = bool(self._host.scene.remove_workspace_node(pin_node.node_id))
        if not removed:
            return ControllerResult(
                False, "Subnode port could not be removed.", payload=False
            )

        self._effects.after_subnode_pin_removed()
        return ControllerResult(True, payload=True)

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None:
        workspace = self._controller.active_workspace()
        self._host.scene.set_node_property(node_id, key, value)
        should_refresh_shell_payload = (
            workspace is not None
            and str(key) in _PIN_REFRESH_PROPERTIES
            and self._is_direct_child_pin_node(
                workspace.nodes.get(node_id), workspace.nodes
            )
        )
        self._effects.after_selected_node_property_changed(
            node_id,
            key,
            value,
            workspace=workspace,
            refresh_scene_payload=should_refresh_shell_payload,
        )

    @staticmethod
    def _is_direct_child_pin_node(
        node: NodeInstance | None,
        workspace_nodes: dict[str, NodeInstance],
    ) -> bool:
        if node is None or not is_subnode_pin_type(node.type_id):
            return False
        parent_node_id = str(node.parent_node_id or "").strip()
        if not parent_node_id:
            return False
        parent_node = workspace_nodes.get(parent_node_id)
        if parent_node is None:
            return False
        return parent_node.type_id == SUBNODE_TYPE_ID

    def on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None:
        workspace = self._controller.active_workspace()
        self._host.scene.set_exposed_port(node_id, key, exposed)
        self._effects.after_selected_port_exposure_changed()

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None:
        self._host.scene.set_node_collapsed(node_id, collapsed)
        self._effects.after_selected_node_collapse_changed()

    def connect_selected_nodes(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        selected = [
            item for item in self._host.scene.selectedItems() if hasattr(item, "node")
        ]
        if len(selected) != 2:
            QMessageBox.information(
                resolve_dialog_parent(self._host),
                "Connect",
                "Select exactly two nodes to connect.",
            )
            return
        first_item = selected[0]
        second_item = selected[1]
        try:
            self._host.scene.connect_nodes(
                first_item.node.node_id, second_item.node.node_id
            )
        except (KeyError, ValueError):
            QMessageBox.warning(
                resolve_dialog_parent(self._host),
                "Connect",
                "No compatible ports found on selected nodes.",
            )
            return
        self._effects.after_ports_connected()

    def duplicate_selected_nodes(self) -> bool:
        duplicated = bool(self._host.scene.duplicate_selected_subgraph())
        if not duplicated:
            return False
        self._effects.after_fragment_duplicated()
        return True

    def wrap_selected_nodes_in_group_backdrop(self) -> bool:
        wrapped = bool(self._host.scene.wrap_selected_nodes_in_group_backdrop())
        if not wrapped:
            return False
        self._effects.after_group_backdrop_wrapped()
        return True

    def group_selected_nodes(self) -> bool:
        grouped = bool(self._host.scene.group_selected_nodes())
        if not grouped:
            return False
        self._effects.after_grouping_changed()
        return True

    def ungroup_selected_nodes(self) -> bool:
        ungrouped = bool(self._host.scene.ungroup_selected_subnode())
        if not ungrouped:
            return False
        self._effects.after_grouping_changed()
        return True

    def run_layout_action(
        self, action: str | None = None, orientation: str | None = None
    ) -> bool:
        before_overlap_pairs = 0
        normalized_action = str(action).strip().lower() if action is not None else None
        if normalized_action is not None:
            before_overlap_pairs = self.count_overlap_pairs(
                self.selected_node_bounds_payload()
            )

        snap_enabled = bool(self._host.snap_to_grid_enabled)
        if normalized_action is not None:
            moved = bool(
                self._host.scene.align_selected_nodes(
                    normalized_action, snap_to_grid=snap_enabled
                )
            )
        else:
            moved = bool(
                self._host.scene.distribute_selected_nodes(
                    orientation, snap_to_grid=snap_enabled
                )
            )
        if not moved:
            return False

        if normalized_action is not None:
            after_overlap_pairs = self.count_overlap_pairs(
                self.selected_node_bounds_payload()
            )
            created_overlap_pairs = max(0, after_overlap_pairs - before_overlap_pairs)
        else:
            created_overlap_pairs = 0

        self._effects.after_layout_action(
            created_overlap_pairs=created_overlap_pairs,
            normalized_action=normalized_action,
        )
        return True

    def selected_node_bounds_payload(self) -> list[tuple[float, float, float, float]]:
        bounds_payload: list[tuple[float, float, float, float]] = []
        selected_node_lookup = self._host.scene.selected_node_lookup
        for node_payload in self._host.scene.nodes_model:
            node_id = str(node_payload.get("node_id", "")).strip()
            if not node_id or not bool(selected_node_lookup.get(node_id, False)):
                continue
            width = float(node_payload.get("width", 0.0))
            height = float(node_payload.get("height", 0.0))
            if width <= 0.0 or height <= 0.0:
                continue
            x = float(node_payload.get("x", 0.0))
            y = float(node_payload.get("y", 0.0))
            bounds_payload.append((x, y, x + width, y + height))
        return bounds_payload

    @staticmethod
    def rectangles_overlap(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        return (
            first[0] < second[2]
            and first[2] > second[0]
            and first[1] < second[3]
            and first[3] > second[1]
        )

    def count_overlap_pairs(
        self, bounds_payload: list[tuple[float, float, float, float]]
    ) -> int:
        overlap_pairs = 0
        for left_index in range(len(bounds_payload)):
            for right_index in range(left_index + 1, len(bounds_payload)):
                if self.rectangles_overlap(
                    bounds_payload[left_index], bounds_payload[right_index]
                ):
                    overlap_pairs += 1
        return overlap_pairs

    def align_selection_left(self) -> bool:
        return self.run_layout_action("left")

    def align_selection_right(self) -> bool:
        return self.run_layout_action("right")

    def align_selection_top(self) -> bool:
        return self.run_layout_action("top")

    def align_selection_bottom(self) -> bool:
        return self.run_layout_action("bottom")

    def distribute_selection_horizontally(self) -> bool:
        return self.run_layout_action(orientation="horizontal")

    def distribute_selection_vertically(self) -> bool:
        return self.run_layout_action(orientation="vertical")

    def _set_selection_same_type_size(
        self, node_ids: tuple[str, ...] | list[object], dimension: str
    ) -> bool:
        changed = bool(
            self._host.scene.set_selected_same_type_size(list(node_ids), dimension)
        )
        if not changed:
            return False
        self._effects.after_layout_action(
            created_overlap_pairs=0, normalized_action=None
        )
        return True

    def set_selection_same_type_width(
        self, node_ids: tuple[str, ...] | list[object]
    ) -> bool:
        return self._set_selection_same_type_size(node_ids, "width")

    def set_selection_same_type_height(
        self, node_ids: tuple[str, ...] | list[object]
    ) -> bool:
        return self._set_selection_same_type_size(node_ids, "height")

    def straighten_selection_connections(self) -> bool:
        moved = bool(self._host.scene.straighten_selected_connections())
        if not moved:
            return False
        self._effects.after_connections_straightened()
        return True

    def clipboard(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return None
        return app.clipboard()

    def write_graph_fragment_to_clipboard(
        self, fragment_payload: dict[str, Any]
    ) -> bool:
        serialized = serialize_graph_fragment_payload(fragment_payload)
        if serialized is None:
            return False
        clipboard = self.clipboard()
        if clipboard is None:
            return False
        mime_data = QMimeData()
        mime_data.setData(GRAPH_FRAGMENT_MIME_TYPE, serialized.encode("utf-8"))
        clipboard.setMimeData(mime_data)
        return True

    def read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None:
        clipboard = self.clipboard()
        if clipboard is None:
            return None
        mime_data = clipboard.mimeData()
        if mime_data is None:
            return None
        if mime_data.hasFormat(GRAPH_FRAGMENT_MIME_TYPE):
            raw_data = bytes(mime_data.data(GRAPH_FRAGMENT_MIME_TYPE))
            try:
                serialized = raw_data.decode("utf-8")
            except UnicodeDecodeError:
                return None
            payload = parse_graph_fragment_payload(serialized)
            if payload is not None:
                return payload
        return None

    def copy_selected_nodes_to_clipboard(self) -> bool:
        fragment_payload = self._host.scene.serialize_selected_subgraph_fragment()
        if fragment_payload is None:
            return False
        copied = self._controller._write_graph_fragment_to_clipboard(fragment_payload)
        if not copied:
            return False
        self._controller.set_clipboard_fragment_signature(
            serialize_graph_fragment_payload(fragment_payload) or ""
        )
        self._controller.set_clipboard_paste_count(0)
        return True

    def cut_selected_nodes_to_clipboard(self) -> bool:
        if not self._controller.copy_selected_nodes_to_clipboard():
            return False
        return bool(self._controller.request_delete_selected_graph_items([]).payload)

    def paste_nodes_from_clipboard(self) -> bool:
        clipboard = self.clipboard()
        if clipboard is None:
            return False
        mime_data = clipboard.mimeData()
        has_graph_fragment_mime = bool(
            mime_data is not None and mime_data.hasFormat(GRAPH_FRAGMENT_MIME_TYPE)
        )
        fragment_payload = self._controller._read_graph_fragment_from_clipboard()
        if fragment_payload is not None:
            return self._paste_graph_fragment_payload(fragment_payload)
        if has_graph_fragment_mime:
            return False
        return self._paste_clipboard_node_items(mime_data)

    def _paste_graph_fragment_payload(self, fragment_payload: dict[str, Any]) -> bool:
        fragment_signature = serialize_graph_fragment_payload(fragment_payload)
        if fragment_signature is None:
            return False
        if fragment_signature != self._controller.clipboard_fragment_signature():
            self._controller.set_clipboard_fragment_signature(fragment_signature)
            self._controller.set_clipboard_paste_count(0)
        frag_center = self._host.scene.fragment_bounds_center(fragment_payload)
        if frag_center is None:
            return False
        parent_node_id = scope_parent_id(
            getattr(self._host.scene, "active_scope_path", ())
        )
        scoped_fragment_payload = self._controller.retarget_fragment_roots(
            fragment_payload,
            target_parent_id=parent_node_id,
        )
        paste_index = self._controller.clipboard_paste_count() + 1
        cascade_x = float(paste_index) * _PASTE_CASCADE_OFFSET_X
        cascade_y = float(paste_index) * _PASTE_CASCADE_OFFSET_Y
        pasted = bool(
            self._host.scene.paste_subgraph_fragment(
                scoped_fragment_payload,
                frag_center[0] + cascade_x,
                frag_center[1] + cascade_y,
            )
        )
        if not pasted:
            return False
        self._controller.set_clipboard_paste_count(
            self._controller.clipboard_paste_count() + 1
        )
        self._effects.after_fragment_pasted()
        return True

    def _paste_clipboard_node_items(self, mime_data: QMimeData | None) -> bool:
        table_items = clipboard_table_paste_items(mime_data)
        if table_items is not None:
            chosen_table_item = self._choose_clipboard_table_paste_item(table_items)
            if chosen_table_item is None:
                return False
            items = (chosen_table_item,)
        else:
            items = classify_clipboard_paste_items(mime_data)
        if not items:
            return False
        item_signature = (
            f"clipboard-paste-items:{clipboard_paste_items_signature(items)}"
        )
        if item_signature != self._controller.clipboard_fragment_signature():
            self._controller.set_clipboard_fragment_signature(item_signature)
            self._controller.set_clipboard_paste_count(0)

        center_x, center_y = self._viewport_scene_center()
        paste_index = self._controller.clipboard_paste_count()
        base_cascade_x = float(paste_index) * _PASTE_CASCADE_OFFSET_X
        base_cascade_y = float(paste_index) * _PASTE_CASCADE_OFFSET_Y
        parent_node_id = scope_parent_id(
            getattr(self._host.scene, "active_scope_path", ())
        )

        created_node_ids: list[str] = []
        for item_index, item in enumerate(items):
            cascade_x = base_cascade_x + (float(item_index) * _PASTE_CASCADE_OFFSET_X)
            cascade_y = base_cascade_y + (float(item_index) * _PASTE_CASCADE_OFFSET_Y)
            node_id = self._create_clipboard_paste_node(
                item,
                x=center_x + cascade_x,
                y=center_y + cascade_y,
                parent_node_id=parent_node_id,
            )
            if node_id:
                created_node_ids.append(node_id)

        if not created_node_ids:
            return False

        self._select_created_clipboard_nodes(created_node_ids)
        self._controller.set_clipboard_paste_count(
            self._controller.clipboard_paste_count() + 1
        )
        self._effects.after_fragment_pasted()
        return True

    def _choose_clipboard_table_paste_item(
        self, items: ClipboardTablePasteItems
    ) -> ClipboardPasteItem | None:
        from PyQt6.QtWidgets import QMessageBox

        dialog = QMessageBox(resolve_dialog_parent(self._host))
        dialog.setWindowTitle("Paste Table")
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setText("Paste copied table as:")
        dialog.setInformativeText(
            "Choose a data input for workflows or a rendered markdown table for notes."
        )
        tabular_button = dialog.addButton(
            "Tabular Data Input", QMessageBox.ButtonRole.AcceptRole
        )
        markdown_button = dialog.addButton(
            "Markdown Table", QMessageBox.ButtonRole.AcceptRole
        )
        dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.setDefaultButton(tabular_button)
        dialog.exec()
        clicked_button = dialog.clickedButton()
        if clicked_button is tabular_button:
            return items.tabular
        if clicked_button is markdown_button:
            return items.markdown
        return None

    def _viewport_scene_center(self) -> tuple[float, float]:
        view = getattr(self._host, "view", None)
        viewport = (
            view.viewport()
            if view is not None and callable(getattr(view, "viewport", None))
            else None
        )
        if (
            view is None
            or viewport is None
            or not callable(getattr(view, "mapToScene", None))
        ):
            return (0.0, 0.0)
        center = view.mapToScene(viewport.rect().center())
        return (float(center.x()), float(center.y()))

    def _create_clipboard_paste_node(
        self,
        item: ClipboardPasteItem,
        *,
        x: float,
        y: float,
        parent_node_id: str | None,
    ) -> str:
        properties = dict(item.properties)
        after_create = None
        if item.artifact is not None:

            def _after_create(node: NodeInstance, mutations) -> bool:  # noqa: ANN001
                staged_ref = self._stage_clipboard_artifact(item, node)
                if not staged_ref:
                    return False
                updates = dict(properties)
                updates[item.artifact.property_key] = staged_ref
                mutations.set_node_properties(node.node_id, updates)
                return True

            after_create = _after_create
            properties = {}

        try:
            return str(
                self._host.scene.create_node_from_type(
                    type_id=item.type_id,
                    x=float(x),
                    y=float(y),
                    parent_node_id=parent_node_id,
                    select_node=False,
                    property_overrides=properties,
                    exposed_port_overrides=(
                        {"source": False}
                        if item.type_id == MEDIA_PANEL_TYPE_ID
                        else None
                    ),
                    after_create=after_create,
                )
                or ""
            )
        except (KeyError, RuntimeError, TypeError, ValueError):
            return ""

    def _stage_clipboard_artifact(
        self, item: ClipboardPasteItem, node: NodeInstance
    ) -> str:
        artifact = item.artifact
        if artifact is None:
            return ""
        controller = getattr(self._host, "project_session_controller", None)
        stage = getattr(controller, "stage_node_artifact_bytes", None)
        if not callable(stage):
            return ""
        try:
            return str(
                stage(
                    data=artifact.data,
                    filename=artifact.filename,
                    mime_type=artifact.mime_type,
                    artifact_prefix=artifact.artifact_prefix,
                    subdirectory=artifact.subdirectory,
                    artifact_kind=artifact.artifact_kind,
                    node_id=node.node_id,
                )
                or ""
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return ""

    def _select_created_clipboard_nodes(self, node_ids: list[str]) -> None:
        if not node_ids:
            return
        self._host.scene.clearSelection()
        for index, node_id in enumerate(node_ids):
            self._host.scene.select_node(node_id, additive=index > 0)

    def undo(self) -> bool:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return False
        entry = self._host.runtime_history.undo_workspace(workspace_id, workspace)
        if entry is None:
            return False
        replayed_entry = HistoryEntry(
            action_type=entry.action_type,
            before=entry.after,
            after=entry.before,
        )
        self._effects.after_history_replayed(workspace_id, replayed_entry)
        return True

    def redo(self) -> bool:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return False
        entry = self._host.runtime_history.redo_workspace(workspace_id, workspace)
        if entry is None:
            return False
        self._effects.after_history_replayed(workspace_id, entry)
        return True

    def request_connect_ports(
        self,
        node_a_id: str,
        port_a: str,
        node_b_id: str,
        port_b: str,
        append_requested: bool = False,
    ) -> ControllerResult[bool]:
        result = self._graph_interactions.connect_ports(
            node_a_id,
            port_a,
            node_b_id,
            port_b,
            append_requested,
        )
        if result.ok:
            self._effects.after_connected_ports_request()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_rewire_edges(
        self,
        edge_ids: list[Any],
        endpoint: str,
        node_id: str,
        port_key: str,
        copy_requested: bool = False,
        append_requested: bool = False,
    ) -> ControllerResult[bool]:
        result = self._graph_interactions.rewire_edges(
            edge_ids,
            endpoint,
            node_id,
            port_key,
            copy_requested,
            append_requested,
        )
        if result.ok:
            if str(node_id or "").strip():
                self._effects.after_connected_ports_request()
            else:
                self._effects.after_edge_removed()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_remove_edge(self, edge_id: str) -> ControllerResult[bool]:
        result = self._graph_interactions.remove_edge(edge_id)
        if result.ok:
            self._effects.after_edge_removed()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_remove_node(self, node_id: str) -> ControllerResult[bool]:
        result = self._graph_interactions.remove_node(node_id)
        if result.ok:
            self._effects.after_node_removed()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_rename_node(self, node_id: str) -> ControllerResult[bool]:
        from PyQt6.QtWidgets import QInputDialog

        workspace = self._host.model.project.workspaces.get(
            self._host.workspace_manager.active_workspace_id()
        )
        if workspace is None:
            return ControllerResult(False, payload=False)
        node = workspace.nodes.get(str(node_id).strip())
        if node is None:
            return ControllerResult(False, payload=False)
        new_title, ok = QInputDialog.getText(
            resolve_dialog_parent(self._host),
            "Rename Node",
            "New name:",
            text=node.title,
        )
        if not ok:
            return ControllerResult(False, payload=False)
        result = self._graph_interactions.rename_node(node.node_id, new_title)
        if result.ok:
            self._effects.after_node_renamed()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_delete_selected_graph_items(
        self, edge_ids: list[Any]
    ) -> ControllerResult[bool]:
        deleted = bool(self._host.scene.delete_selected_graph_items(edge_ids))
        if deleted:
            self._effects.after_selected_graph_items_deleted()
            return ControllerResult(True, payload=True)
        return ControllerResult(
            False, "No selected graph items to remove.", payload=False
        )
