from __future__ import annotations

from unittest.mock import patch

from tests.main_window_shell.base import *  # noqa: F401,F403
from tests.qt_wait import wait_for_condition_or_raise
from PyQt6.QtCore import QObject, QMetaObject, QPoint, QPointF, Qt
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtQml import QJSValue
from PyQt6.QtTest import QTest


class MainWindowShellViewLibraryInspectorTests(SharedMainWindowShellTestBase):
    def _walk_items(self, item: QQuickItem):
        yield item
        for child in item.childItems():
            yield from self._walk_items(child)

    def _pane_child_item(self, pane: QObject, object_name: str) -> QQuickItem:
        self.assertIsInstance(pane, QQuickItem)
        for item in self._walk_items(pane):
            if item.objectName() == object_name:
                return item
        self.fail(f"Could not find {object_name!r} under pane {pane.objectName()!r}.")

    def _item_widget_point(self, item: QQuickItem, x: float, y: float) -> QPoint:
        item_window = item.window()
        self.assertIsNotNone(item_window)
        scene_point = item.mapToScene(QPointF(x, y))
        global_point = item_window.mapToGlobal(
            QPoint(round(scene_point.x()), round(scene_point.y()))
        )
        return self.window.quick_widget.mapFromGlobal(global_point)

    def _move_mouse_to_shell_center(self) -> None:
        QTest.mouseMove(
            self.window.quick_widget,
            QPoint(
                self.window.quick_widget.width() // 2,
                self.window.quick_widget.height() // 2,
            ),
        )
        self.app.processEvents()

    def _inspector_object(self, name: str) -> QObject:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        item = root_object.findChild(QObject, name)
        self.assertIsNotNone(item)
        return item

    def _inspector_property_object(self, object_name: str, property_key: str) -> QQuickItem:
        item = self._find_inspector_property_object(object_name, property_key)
        if item is not None:
            return item
        self.fail(f"Could not find {object_name!r} for property {property_key!r}.")

    def _find_inspector_property_object(self, object_name: str, property_key: str) -> QQuickItem | None:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        for item in self._walk_items(root_object):
            if item.objectName() != object_name:
                continue
            if str(item.property("propertyKey")) != property_key:
                continue
            if not bool(item.property("visible")):
                continue
            return item
        return None

    @staticmethod
    def _variant_value(value):  # noqa: ANN001
        if isinstance(value, QJSValue):
            return value.toVariant()
        return value

    def _library_item(self, type_id: str) -> dict[str, object]:
        return next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("type_id") == type_id
        )

    def _strip_child(self, strip: QObject, object_name: str) -> QObject:
        child = strip.findChild(QObject, object_name)
        self.assertIsNotNone(child)
        return child

    def _tab_strip_slots(self, strip: QObject) -> list[QQuickItem]:
        slots = strip.property("tabSlots")
        if isinstance(slots, QJSValue):
            slots = slots.toVariant()
        return sorted(
            [slot for slot in (slots or []) if isinstance(slot, QQuickItem)],
            key=lambda slot: float(slot.property("x")),
        )

    def _active_tab_slot(self, strip: QObject) -> QQuickItem:
        for slot in self._tab_strip_slots(strip):
            for child in slot.children():
                if isinstance(child, QQuickItem) and bool(child.property("active")):
                    return slot
        self.fail(f"Expected an active tab slot under strip {strip.objectName()!r}.")

    def _tab_slot_fully_visible(self, strip: QObject, slot: QQuickItem) -> bool:
        viewport_width = float(strip.property("tabsViewportWidth"))
        content_x = float(strip.property("tabsContentX"))
        slot_left = float(slot.property("x")) - content_x
        slot_right = slot_left + float(slot.property("width"))
        return slot_left >= -0.5 and slot_right <= viewport_width + 0.5

    def _scene_node_payload(self, node_id: str) -> dict[str, object]:
        return next(
            node
            for node in self.window.scene.nodes_model
            if node.get("node_id") == node_id
        )

    def _screen_point_for_port(self, node_id: str, port_key: str) -> tuple[float, float]:
        graph_canvas = self._graph_canvas_item()
        node_payload = self._scene_node_payload(node_id)
        port_payload = next(
            port
            for port in node_payload.get("ports", [])
            if port.get("key") == port_key
        )
        point = self._variant_value(graph_canvas._scenePortPoint(node_payload, port_payload, 0, 0))
        screen_x = float(graph_canvas.sceneToScreenX(point["x"]))
        screen_y = float(graph_canvas.sceneToScreenY(point["y"]))
        return screen_x, screen_y

    def test_qml_side_panes_share_collapsible_shell_behavior(self) -> None:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        library_pane = root_object.findChild(QObject, "libraryPane")
        inspector_pane = root_object.findChild(QObject, "inspectorPane")

        self.assertIsNotNone(library_pane)
        self.assertIsNotNone(inspector_pane)

        for pane in (library_pane, inspector_pane):
            self.assertFalse(bool(pane.property("paneCollapsed")))
            QMetaObject.invokeMethod(pane, "collapsePane")
            wait_for_condition_or_raise(
                lambda pane=pane: float(pane.property("width")) <= 1.0,
                timeout_ms=2500,
                poll_interval_ms=20,
                app=self.app,
                timeout_message=lambda pane=pane: (
                    f"Pane width did not satisfy predicate within 2500ms: {pane.property('width')}"
                ),
            )
            self.assertTrue(bool(pane.property("paneCollapsed")))
            self.assertLessEqual(float(pane.property("width")), 1.0)

            QMetaObject.invokeMethod(pane, "expandPane")
            wait_for_condition_or_raise(
                lambda pane=pane: float(pane.property("width")) > 200.0,
                timeout_ms=2500,
                poll_interval_ms=20,
                app=self.app,
                timeout_message=lambda pane=pane: (
                    f"Pane width did not satisfy predicate within 2500ms: {pane.property('width')}"
                ),
            )
            self.assertFalse(bool(pane.property("paneCollapsed")))
            self.assertGreater(float(pane.property("width")), 200.0)

    def test_qml_collapsed_side_pane_handles_reveal_only_on_edge_hover(self) -> None:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        library_pane = root_object.findChild(QObject, "libraryPane")
        inspector_pane = root_object.findChild(QObject, "inspectorPane")

        self.assertIsNotNone(library_pane)
        self.assertIsNotNone(inspector_pane)

        for pane in (library_pane, inspector_pane):
            self._move_mouse_to_shell_center()
            QMetaObject.invokeMethod(pane, "collapsePane")
            wait_for_condition_or_raise(
                lambda pane=pane: float(pane.property("width")) <= 1.0,
                timeout_ms=2500,
                poll_interval_ms=20,
                app=self.app,
                timeout_message=lambda pane=pane: (
                    f"Pane width did not satisfy predicate within 2500ms: {pane.property('width')}"
                ),
            )

            handle = self._pane_child_item(pane, "collapsedSidePaneHandle")
            reveal_zone = self._pane_child_item(pane, "collapsedSidePaneRevealZone")
            edge_point = self._item_widget_point(
                reveal_zone,
                max(1.0, float(reveal_zone.width()) * 0.5),
                float(reveal_zone.height()) * 0.5,
            )

            wait_for_condition_or_raise(
                lambda pane=pane, handle=handle: (
                    not bool(pane.property("collapsedHandleRevealed"))
                    and float(handle.property("opacity")) < 0.05
                ),
                timeout_ms=600,
                poll_interval_ms=20,
                app=self.app,
                timeout_message="Collapsed side pane handle did not start hidden.",
            )

            QTest.mouseMove(self.window.quick_widget, edge_point)
            wait_for_condition_or_raise(
                lambda pane=pane, handle=handle: (
                    bool(pane.property("collapsedHandleRevealed"))
                    and float(handle.property("opacity")) > 0.8
                ),
                timeout_ms=800,
                poll_interval_ms=20,
                app=self.app,
                timeout_message="Collapsed side pane handle did not reveal near the edge.",
            )

            self._move_mouse_to_shell_center()
            wait_for_condition_or_raise(
                lambda pane=pane, handle=handle: (
                    not bool(pane.property("collapsedHandleRevealed"))
                    and float(handle.property("opacity")) < 0.1
                ),
                timeout_ms=800,
                poll_interval_ms=20,
                app=self.app,
                timeout_message="Collapsed side pane handle stayed visible away from the edge.",
            )

            QTest.mouseMove(self.window.quick_widget, edge_point)
            wait_for_condition_or_raise(
                lambda pane=pane, handle=handle: (
                    bool(pane.property("collapsedHandleRevealed"))
                    and float(handle.property("opacity")) > 0.8
                ),
                timeout_ms=800,
                poll_interval_ms=20,
                app=self.app,
                timeout_message="Collapsed side pane handle did not reveal before expanding.",
            )
            handle_point = self._item_widget_point(
                handle,
                float(handle.width()) * 0.5,
                float(handle.height()) * 0.5,
            )
            QTest.mouseClick(
                self.window.quick_widget,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                handle_point,
            )
            wait_for_condition_or_raise(
                lambda pane=pane: (
                    not bool(pane.property("paneCollapsed"))
                    and float(pane.property("width")) > 200.0
                ),
                timeout_ms=2500,
                poll_interval_ms=20,
                app=self.app,
                timeout_message=lambda pane=pane: (
                    f"Pane did not expand from hover-revealed handle: {pane.property('width')}"
                ),
            )

    def test_qml_rect_selection_supports_replace_and_additive_modes(self) -> None:
        node_a = self.window.scene.add_node_from_type("core.start", x=20.0, y=20.0)
        node_b = self.window.scene.add_node_from_type("core.end", x=360.0, y=30.0)
        self.app.processEvents()

        self.window.scene.select_nodes_in_rect(0.0, 0.0, 280.0, 180.0)
        self.app.processEvents()
        selected_after_replace = set(self.window.scene.selected_node_lookup)
        self.assertEqual(selected_after_replace, {node_a})

        self.window.scene.select_nodes_in_rect(300.0, 0.0, 700.0, 200.0, True)
        self.app.processEvents()
        selected_after_additive = set(self.window.scene.selected_node_lookup)
        self.assertEqual(selected_after_additive, {node_a, node_b})

    def test_qml_parallel_edges_between_same_nodes_use_distinct_lanes(self) -> None:
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.logger", x=320.0, y=60.0)
        self.assertTrue(self.window.scene.set_port_locked(target_id, "message", False))
        self.window.scene.set_node_collapsed(source_id, True)
        self.window.scene.set_node_collapsed(target_id, True)
        self.app.processEvents()

        edge_a = self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        edge_b = self.window.scene.add_edge(source_id, "trigger", target_id, "message")
        self.app.processEvents()

        edges_by_id = {item["edge_id"]: item for item in self.window.scene.edges_model}
        self.assertIn(edge_a, edges_by_id)
        self.assertIn(edge_b, edges_by_id)
        c1_gap = abs(edges_by_id[edge_a]["c1y"] - edges_by_id[edge_b]["c1y"])
        c2_gap = abs(edges_by_id[edge_a]["c2y"] - edges_by_id[edge_b]["c2y"])
        self.assertGreater(c1_gap, 8.0)
        self.assertGreater(c2_gap, 8.0)

    def test_qml_backward_edge_routes_outside_connected_node_bounds(self) -> None:
        source_id = self.window.scene.add_node_from_type("core.start", x=360.0, y=80.0)
        target_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=220.0)
        self.app.processEvents()

        self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        nodes_by_id = {item["node_id"]: item for item in self.window.scene.nodes_model}
        source_node = nodes_by_id[source_id]
        target_node = nodes_by_id[target_id]
        edge = self.window.scene.edges_model[0]

        source_right = source_node["x"] + source_node["width"]
        target_left = target_node["x"]
        source_top = source_node["y"]
        source_bottom = source_node["y"] + source_node["height"]
        target_top = target_node["y"]
        target_bottom = target_node["y"] + target_node["height"]

        self.assertGreater(edge["c1x"], source_right)
        self.assertLess(edge["c2x"], target_left)
        self.assertEqual(edge["route"], "pipe")

        pipe_points = edge["pipe_points"]
        self.assertGreaterEqual(len(pipe_points), 4)
        self.assertAlmostEqual(pipe_points[0]["x"], edge["sx"], places=4)
        self.assertAlmostEqual(pipe_points[0]["y"], edge["sy"], places=4)
        self.assertAlmostEqual(pipe_points[-1]["x"], edge["tx"], places=4)
        self.assertAlmostEqual(pipe_points[-1]["y"], edge["ty"], places=4)
        self.assertGreater(pipe_points[1]["x"], source_right)
        self.assertLess(pipe_points[-2]["x"], target_left)
        for index in range(1, len(pipe_points)):
            start = pipe_points[index - 1]
            end = pipe_points[index]
            self.assertTrue(
                abs(start["x"] - end["x"]) < 0.001 or abs(start["y"] - end["y"]) < 0.001,
                msg=f"segment {index - 1}->{index} is not orthogonal: {start} -> {end}",
            )
        horizontal_lanes = [
            start["y"]
            for index, start in enumerate(pipe_points[:-1])
            if abs(start["y"] - pipe_points[index + 1]["y"]) < 0.001
        ]
        self.assertTrue(
            any(source_bottom < y < target_top for y in horizontal_lanes),
            msg=f"expected a routing lane between nodes, got {pipe_points}",
        )

    def test_qml_library_filter_slots_apply_category_direction_and_type(self) -> None:
        self.window.set_library_query("")
        self.window.set_library_category("Input / Output")
        self.window.set_library_direction("in")
        self.window.set_library_data_type("path")
        self.app.processEvents()

        type_ids = {item["type_id"] for item in self.window.filtered_node_library_items}
        self.assertIn("io.file_read", type_ids)
        self.assertIn("io.file_write", type_ids)
        self.assertIn("io.excel_read", type_ids)
        self.assertIn("io.excel_write", type_ids)
        self.assertNotIn("core.logger", type_ids)

    def test_qml_graph_canvas_library_drop_on_flowchart_port_autoconnects_neutral_side(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        target_id = self.window.scene.add_node_from_type("passive.flowchart.process", x=360.0, y=120.0)
        self.app.processEvents()

        graph_canvas = self._graph_canvas_item()
        payload = self._library_item("passive.flowchart.process")
        screen_x, screen_y = self._screen_point_for_port(target_id, "right")
        graph_canvas.updateLibraryDropPreview(screen_x + 6.0, screen_y, payload)
        self.app.processEvents()

        preview = self._variant_value(graph_canvas.property("dropPreviewPort"))
        self.assertEqual(
            preview,
            {
                "node_id": target_id,
                "port_key": "right",
                "direction": "neutral",
            },
        )

        graph_canvas.performLibraryDrop(screen_x + 6.0, screen_y, payload)
        self.app.processEvents()

        self.assertEqual(len(workspace.edges), 1)
        new_node_id = self.window.scene.selected_node_id()
        self.assertTrue(new_node_id)
        edge = next(iter(workspace.edges.values()))
        self.assertEqual(edge.source_node_id, target_id)
        self.assertEqual(edge.source_port_key, "right")
        self.assertEqual(edge.target_node_id, new_node_id)
        self.assertEqual(edge.target_port_key, "left")

    def test_qml_flowchart_connection_quick_insert_preserves_top_port_as_source(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        source_id = self.window.scene.add_node_from_type("passive.flowchart.process", x=80.0, y=140.0)
        self.app.processEvents()

        opened = self.window.request_open_connection_quick_insert(
            source_id,
            "top",
            180.0,
            80.0,
            300.0,
            160.0,
        )
        self.assertTrue(opened)
        self.app.processEvents()

        self.window.set_connection_quick_insert_query("end")
        self.app.processEvents()

        results = self.window.connection_quick_insert_results
        self.assertTrue(results)
        chosen_index = next(
            index
            for index, item in enumerate(results)
            if item.get("type_id") == "passive.flowchart.end"
        )

        created = self.window.request_connection_quick_insert_choose(chosen_index)
        self.assertTrue(created)
        self.app.processEvents()

        self.assertFalse(self.window.connection_quick_insert_open)
        self.assertEqual(len(workspace.edges), 1)
        new_node_id = self.window.scene.selected_node_id()
        self.assertTrue(new_node_id)
        edge = next(iter(workspace.edges.values()))
        self.assertEqual(edge.source_node_id, source_id)
        self.assertEqual(edge.source_port_key, "top")
        self.assertEqual(edge.target_node_id, new_node_id)
        self.assertEqual(edge.target_port_key, "left")

    def test_qml_subnode_library_category_contains_pin_nodes(self) -> None:
        self.window.set_library_query("")
        self.window.set_library_category("Subnode")
        self.window.set_library_direction("")
        self.window.set_library_data_type("")
        self.app.processEvents()

        library_items = {
            item["type_id"]: item
            for item in self.window.filtered_node_library_items
        }
        self.assertIn("core.subnode_input", library_items)
        self.assertIn("core.subnode_output", library_items)
        self.assertEqual(library_items["core.subnode_input"]["category"], "Subnode")
        self.assertEqual(library_items["core.subnode_output"]["category"], "Subnode")
        pin_types = self.window.pin_data_type_options
        self.assertIn("any", pin_types)
        self.assertIn("json", pin_types)
        self.assertIn("str", pin_types)

    def test_qml_selected_node_inspector_mutations_update_graph_model(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=60.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        self.assertTrue(self.window.has_selected_node)
        property_keys = {item["key"] for item in self.window.selected_node_property_items}
        self.assertIn("message", property_keys)
        port_keys = {item["key"] for item in self.window.selected_node_port_items}
        self.assertIn("exec_in", port_keys)
        self.assertIn("message", port_keys)

        self.window.set_selected_node_property("message", "updated in qml inspector")
        self.window.set_selected_port_exposed("message", False)
        self.window.set_selected_node_collapsed(True)
        self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties["message"], "updated in qml inspector")
        self.assertFalse(node.exposed_ports["message"])
        self.assertTrue(node.collapsed)

    def test_qml_inspector_required_port_toggle_is_disabled_and_noops(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=60.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        inspector_pane = self._inspector_object("inspectorPane")
        toggles_by_key = {
            str(item.property("portKey")): item
            for item in self._walk_items(inspector_pane)
            if item.objectName() == "inspectorPortExposedToggle"
        }

        self.assertIn("exec_in", toggles_by_key)
        self.assertIn("message", toggles_by_key)
        self.assertFalse(bool(toggles_by_key["exec_in"].property("enabled")))
        self.assertTrue(bool(toggles_by_key["exec_in"].property("checked")))
        self.assertTrue(bool(toggles_by_key["message"].property("enabled")))

        self.window.set_selected_port_exposed("exec_in", False)
        self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertTrue(bool(node.exposed_ports.get("exec_in", True)))
        port_items = {item["key"]: item for item in self.window.selected_node_port_items}
        self.assertTrue(bool(port_items["exec_in"]["required"]))
        self.assertTrue(bool(port_items["exec_in"]["exposed"]))

    def test_qml_inspector_cards_swap_between_empty_and_selected_states(self) -> None:
        empty_card = self._inspector_object("inspectorEmptyStateCard")
        node_definition_card = self._inspector_object("inspectorNodeDefinitionCard")
        port_management_card = self._inspector_object("inspectorPortManagementCard")

        self.assertTrue(bool(empty_card.property("visible")))
        self.assertFalse(bool(node_definition_card.property("visible")))
        self.assertFalse(bool(port_management_card.property("visible")))

        node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=60.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        self.assertFalse(bool(empty_card.property("visible")))
        self.assertTrue(bool(node_definition_card.property("visible")))
        self.assertTrue(bool(port_management_card.property("visible")))

    def test_qml_inspector_property_variant_loader_defaults_to_smart_groups(self) -> None:
        self.window.shell_inspector_presenter.set_property_pane_variant("smart_groups")
        self.app.processEvents()

        node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=60.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        loader = self._inspector_object("inspectorPropertyVariantLoader")
        self.assertTrue(bool(loader.property("visible")))
        self.assertTrue(bool(loader.property("active")))

        body = self._inspector_object("inspectorSmartGroupsBody")
        self.assertIsNotNone(body)

    def test_qml_inspector_property_variant_loader_switches_with_preference(self) -> None:
        node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=60.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        presenter = self.window.shell_inspector_presenter
        try:
            presenter.set_property_pane_variant("accordion_cards")
            self.app.processEvents()
            self.assertIsNotNone(self._inspector_object("inspectorAccordionCardsBody"))

            presenter.set_property_pane_variant("palette")
            self.app.processEvents()
            self.assertIsNotNone(self._inspector_object("inspectorPaletteBody"))

            presenter.set_property_pane_variant("smart_groups")
            self.app.processEvents()
            self.assertIsNotNone(self._inspector_object("inspectorSmartGroupsBody"))
        finally:
            presenter.set_property_pane_variant("smart_groups")
            self.app.processEvents()

    def test_qml_inspector_port_direction_switch_reselects_visible_port(self) -> None:
        node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=60.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        inspector_pane = self._inspector_object("inspectorPane")
        inputs_tab = self._inspector_object("inspectorInputsTab")
        outputs_tab = self._inspector_object("inspectorOutputsTab")

        input_keys = {
            item["key"]
            for item in self.window.selected_node_port_items
            if item["direction"] == "in"
        }
        output_keys = {
            item["key"]
            for item in self.window.selected_node_port_items
            if item["direction"] == "out"
        }

        self.assertIn(str(inspector_pane.property("selectedPortKey")), input_keys)
        self.assertTrue(bool(inputs_tab.property("selectedStyle")))
        self.assertFalse(bool(outputs_tab.property("selectedStyle")))

        inspector_pane.setProperty("activePortDirection", "out")
        self.app.processEvents()

        self.assertIn(str(inspector_pane.property("selectedPortKey")), output_keys)
        self.assertFalse(bool(inputs_tab.property("selectedStyle")))
        self.assertTrue(bool(outputs_tab.property("selectedStyle")))

    def test_qml_inspector_background_focus_commits_inline_port_rename(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        self.window.scene.focus_node(shell_id)
        self.app.processEvents()

        port_node_id = self.window.request_add_selected_subnode_pin("out")
        self.assertTrue(port_node_id)
        inspector_pane = self._inspector_object("inspectorPane")
        inspector_pane.setProperty("activePortDirection", "out")
        inspector_pane.setProperty("editingPortKey", port_node_id)
        inspector_pane.setProperty("editingPortLabel", "Committed From Pane")
        self.app.processEvents()

        QMetaObject.invokeMethod(inspector_pane, "focusInspectorBackground")
        self.app.processEvents()

        self.assertEqual(str(inspector_pane.property("editingPortKey")), "")
        self.assertEqual(workspace.nodes[port_node_id].properties["label"], "Committed From Pane")

    def test_graph_canvas_command_bridge_commits_port_label_rename(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        node_id = self.window.scene.add_node_from_type("core.logger", x=180.0, y=120.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        self.window.graph_canvas_command_bridge.set_node_port_label(
            node_id,
            "message",
            "Renamed From Canvas",
        )
        self.app.processEvents()

        self.assertEqual(workspace.nodes[node_id].port_labels["message"], "Renamed From Canvas")

    def test_graph_canvas_command_bridge_commits_subnode_shell_port_label_rename(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        self.window.scene.focus_node(shell_id)
        self.app.processEvents()

        port_node_id = self.window.request_add_selected_subnode_pin("out")
        self.assertTrue(port_node_id)

        self.window.graph_canvas_command_bridge.set_node_port_label(
            shell_id,
            port_node_id,
            "Renamed Shell Output",
        )
        self.app.processEvents()

        self.assertEqual(workspace.nodes[port_node_id].properties["label"], "Renamed Shell Output")

    def test_graph_canvas_command_bridge_commits_subnode_pin_port_label_rename(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        self.window.scene.focus_node(shell_id)
        self.app.processEvents()

        port_node_id = self.window.request_add_selected_subnode_pin("out")
        self.assertTrue(port_node_id)
        self.assertTrue(self.window.request_open_subnode_scope(shell_id))
        self.window.scene.focus_node(port_node_id)
        self.app.processEvents()

        self.window.graph_canvas_command_bridge.set_node_port_label(
            port_node_id,
            "pin",
            "Renamed Inner Pin",
        )
        self.app.processEvents()

        self.assertEqual(workspace.nodes[port_node_id].properties["label"], "Renamed Inner Pin")

    def test_qml_inspector_delete_selected_subnode_port_removes_pin_node(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        self.window.scene.focus_node(shell_id)
        self.app.processEvents()

        first_port_id = self.window.request_add_selected_subnode_pin("out")
        second_port_id = self.window.request_add_selected_subnode_pin("out")
        self.assertTrue(first_port_id)
        self.assertTrue(second_port_id)
        inspector_pane = self._inspector_object("inspectorPane")
        inspector_pane.setProperty("activePortDirection", "out")
        inspector_pane.setProperty("selectedPortKey", second_port_id)
        self.app.processEvents()

        QMetaObject.invokeMethod(inspector_pane, "deleteSelectedPort")
        self.app.processEvents()

        self.assertIn(first_port_id, workspace.nodes)
        self.assertNotIn(second_port_id, workspace.nodes)
        remaining_output_keys = {
            item["key"]
            for item in self.window.selected_node_port_items
            if item["direction"] == "out"
        }
        self.assertEqual(remaining_output_keys, {first_port_id})
        self.assertEqual(str(inspector_pane.property("selectedPortKey")), first_port_id)

    def test_qml_selected_node_header_metadata_exposes_clean_fields(self) -> None:
        first_node_id = self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        second_node_id = self.window.scene.add_node_from_type("core.start", x=120.0, y=0.0)
        self.window.scene.focus_node(second_node_id)
        self.app.processEvents()

        self.assertEqual(self.window.selected_node_title, "Start")
        self.assertEqual(self.window.selected_node_subtitle, "Entry point for DAG execution.")
        self.assertNotIn("\\n", self.window.selected_node_summary)
        self.assertIn("\n", self.window.selected_node_summary)
        self.assertNotIn(second_node_id, self.window.selected_node_summary)

        metadata = {item["label"]: item["value"] for item in self.window.selected_node_header_items}
        self.assertEqual(metadata["Category"], "Core")
        self.assertEqual(metadata["ID"], "2")
        self.assertEqual(set(metadata), {"Category", "ID"})
        self.assertNotEqual(first_node_id, second_node_id)

    def test_qml_pin_inspector_updates_parent_shell_ports(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        custom_data_type = "pressure_tensor"

        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        self.assertTrue(self.window.request_open_subnode_scope(shell_id))
        pin_id = self.window.scene.add_node_from_type("core.subnode_input", x=40.0, y=40.0)
        self.window.scene.focus_node(pin_id)
        self.app.processEvents()

        self.assertTrue(self.window.selected_node_is_subnode_pin)
        self.assertEqual(
            [item["key"] for item in self.window.selected_node_property_items],
            ["label", "kind", "data_type"],
        )
        self.assertEqual(self.window.selected_node_port_items, [])

        self.window.set_selected_node_property("label", "Payload In")
        self.window.set_selected_node_property("kind", "data")
        self.window.set_selected_node_property("data_type", custom_data_type)
        self.app.processEvents()

        self.assertTrue(self.window.request_navigate_scope_parent())
        self.window.scene.focus_node(shell_id)
        self.app.processEvents()

        shell_payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == shell_id)
        shell_ports = {port["key"]: port for port in shell_payload["ports"]}
        self.assertIn(pin_id, shell_ports)
        self.assertEqual(shell_ports[pin_id]["label"], "Payload In")
        self.assertEqual(shell_ports[pin_id]["kind"], "data")
        self.assertEqual(shell_ports[pin_id]["data_type"], custom_data_type)

        shell_port_items = {item["key"]: item for item in self.window.selected_node_port_items}
        self.assertIn(pin_id, shell_port_items)
        self.assertEqual(shell_port_items[pin_id]["label"], "Payload In")
        self.assertEqual(workspace.nodes[pin_id].parent_node_id, shell_id)
        self.assertIn(custom_data_type, self.window.pin_data_type_options)

    def test_qml_pin_inspector_hides_port_management_card(self) -> None:
        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        self.assertTrue(self.window.request_open_subnode_scope(shell_id))
        pin_id = self.window.scene.add_node_from_type("core.subnode_input", x=40.0, y=40.0)
        self.window.scene.focus_node(pin_id)
        self.app.processEvents()

        node_definition_card = self._inspector_object("inspectorNodeDefinitionCard")
        port_management_card = self._inspector_object("inspectorPortManagementCard")
        pin_hint_banner = self._inspector_object("inspectorPinHintBanner")

        self.assertTrue(bool(node_definition_card.property("visible")))
        self.assertFalse(bool(port_management_card.property("visible")))
        self.assertTrue(bool(pin_hint_banner.property("visible")))

    def test_qml_node_payload_port_list_tracks_exposed_ports(self) -> None:
        node_id = self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        initial_nodes = self.window.scene.nodes_model
        start_payload = next(item for item in initial_nodes if item["node_id"] == node_id)
        initial_ports = {port["key"] for port in start_payload["ports"]}
        self.assertEqual(initial_ports, {"exec_out", "trigger"})

        self.window.scene.set_exposed_port(node_id, "exec_out", False)
        self.app.processEvents()

        updated_nodes = self.window.scene.nodes_model
        updated_payload = next(item for item in updated_nodes if item["node_id"] == node_id)
        updated_ports = {port["key"] for port in updated_payload["ports"]}
        self.assertEqual(updated_ports, {"trigger"})

    def test_qml_node_payload_projects_locked_optional_state_and_manual_lock_toggle_roundtrips_undo_redo(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        node_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=80.0)
        self.app.processEvents()

        def ports_by_key() -> dict[str, dict[str, object]]:
            payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == node_id)
            return {str(port["key"]): port for port in payload["ports"]}

        self.assertTrue(bool(ports_by_key()["message"]["locked"]))
        self.assertTrue(bool(ports_by_key()["message"]["optional"]))
        self.assertFalse(bool(ports_by_key()["exec_in"]["optional"]))

        self.window.runtime_history.clear_workspace(workspace_id)
        self.assertTrue(self.window.scene.set_port_locked(node_id, "message", False))
        self.app.processEvents()

        self.assertFalse(bool(ports_by_key()["message"]["locked"]))
        self.assertFalse(bool(workspace.nodes[node_id].locked_ports["message"]))
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 1)

        self.window.action_undo.trigger()
        wait_for_condition_or_raise(
            lambda: bool(ports_by_key()["message"]["locked"]),
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for locked-port undo payload refresh.",
        )
        self.assertTrue(bool(workspace.nodes[node_id].locked_ports["message"]))

        self.window.action_redo.trigger()
        wait_for_condition_or_raise(
            lambda: not bool(ports_by_key()["message"]["locked"]),
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for locked-port redo payload refresh.",
        )
        self.assertFalse(bool(workspace.nodes[node_id].locked_ports["message"]))

    def test_qml_view_hide_filters_are_view_local_and_filter_payload_ports(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        primary_view_id = workspace.active_view_id
        node_id = self.window.scene.add_node_from_type("core.logger", x=240.0, y=120.0)
        self.app.processEvents()

        def port_keys() -> set[str]:
            payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == node_id)
            return {str(port["key"]) for port in payload["ports"]}

        self.assertEqual(port_keys(), {"exec_in", "exec_out", "message"})

        self.window.runtime_history.clear_workspace(workspace_id)
        self.assertTrue(self.window.scene.set_hide_locked_ports(True))
        wait_for_condition_or_raise(
            lambda: port_keys() == {"exec_in", "exec_out"},
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for hide-locked payload filtering.",
        )
        self.assertTrue(bool(workspace.views[primary_view_id].hide_locked_ports))
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 1)

        self.window.action_undo.trigger()
        wait_for_condition_or_raise(
            lambda: port_keys() == {"exec_in", "exec_out", "message"},
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for hide-locked undo payload refresh.",
        )
        self.assertFalse(bool(workspace.views[primary_view_id].hide_locked_ports))

        self.window.action_redo.trigger()
        wait_for_condition_or_raise(
            lambda: port_keys() == {"exec_in", "exec_out"},
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for hide-locked redo payload refresh.",
        )
        self.assertTrue(bool(workspace.views[primary_view_id].hide_locked_ports))

        secondary_view_id = self.window.workspace_manager.create_view(workspace_id, name="Filtered")
        self.app.processEvents()
        self.window.scene.set_hide_locked_ports(False)
        self.window.scene.set_hide_optional_ports(True)
        wait_for_condition_or_raise(
            lambda: port_keys() == {"exec_in"},
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for hide-optional payload filtering.",
        )
        self.assertFalse(bool(workspace.views[secondary_view_id].hide_locked_ports))
        self.assertTrue(bool(workspace.views[secondary_view_id].hide_optional_ports))

        self.window.request_switch_view(primary_view_id)
        wait_for_condition_or_raise(
            lambda: port_keys() == {"exec_in", "exec_out"},
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for primary-view payload restore.",
        )
        self.assertTrue(bool(workspace.views[primary_view_id].hide_locked_ports))
        self.assertFalse(bool(workspace.views[primary_view_id].hide_optional_ports))

        self.window.request_switch_view(secondary_view_id)
        wait_for_condition_or_raise(
            lambda: port_keys() == {"exec_in"},
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for secondary-view payload restore.",
        )

    def test_qml_node_payload_exposes_inline_property_metadata_for_supported_nodes(self) -> None:
        node_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == node_id)
        inline_items = {item["key"]: item for item in payload["inline_properties"]}
        self.assertEqual(set(inline_items), {"message", "level"})
        self.assertEqual(inline_items["message"]["inline_editor"], "text")
        self.assertEqual(inline_items["level"]["inline_editor"], "enum")
        self.assertGreater(payload["height"], 60.0)

    def test_qml_inline_property_payload_tracks_value_changes_and_input_override(self) -> None:
        logger_id = self.window.scene.add_node_from_type("core.logger", x=260.0, y=120.0)
        constant_id = self.window.scene.add_node_from_type("core.constant", x=20.0, y=120.0)
        self.window.scene.focus_node(logger_id)
        self.window.set_selected_node_property("message", "inline update")
        self.assertTrue(self.window.scene.set_port_locked(logger_id, "message", False))
        self.window.request_connect_ports(constant_id, "as_text", logger_id, "message")
        self.app.processEvents()

        payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == logger_id)
        inline_items = {item["key"]: item for item in payload["inline_properties"]}
        self.assertEqual(inline_items["message"]["value"], "inline update")
        self.assertTrue(inline_items["message"]["overridden_by_input"])
        self.assertEqual(inline_items["message"]["input_port_label"], "message")

    def test_qml_dpf_model_path_property_is_overridden_by_result_file_input(self) -> None:
        model_id = self.window.scene.add_node_from_type("dpf.model", x=260.0, y=120.0)
        result_file_id = self.window.scene.add_node_from_type("dpf.result_file", x=20.0, y=120.0)
        self.window.scene.focus_node(model_id)
        self.window.set_selected_node_property("path", "C:/tmp/example.rst")
        self.window.request_connect_ports(result_file_id, "result_file", model_id, "result_file")
        self.app.processEvents()

        property_items = {item["key"]: item for item in self.window.selected_node_property_items}
        self.assertEqual(property_items["path"]["value"], "C:/tmp/example.rst")
        self.assertTrue(property_items["path"]["overridden_by_input"])
        self.assertEqual(property_items["path"]["input_port_label"], "result_file")
        self.assertEqual(property_items["path"]["override_reason"], "Driven by result_file")

        node_payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == model_id)
        ports_by_key = {port["key"]: port for port in node_payload["ports"]}
        self.assertTrue(ports_by_key["path"]["inactive"])
        self.assertEqual(ports_by_key["path"]["inactive_source_key"], "result_file")
        self.assertEqual(ports_by_key["path"]["inactive_reason"], "Driven by result_file")

        self.assertIsNone(self._find_inspector_property_object("inspectorPathEditor", "path"))
        self.assertIsNone(self._find_inspector_property_object("inspectorPathBrowseButton", "path"))
        inactive_chip = self._inspector_property_object("inspectorPropertyInactiveChip", "path")
        override_reason = self._inspector_property_object("inspectorPropertyOverrideReason", "path")
        self.assertTrue(bool(inactive_chip.property("visible")))
        self.assertEqual(str(override_reason.property("text")), "Driven by result_file")

    def test_viewport_commands_frame_all_frame_selection_and_center_selection(self) -> None:
        node_a = self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        self.window.scene.add_node_from_type("core.end", x=540.0, y=260.0)
        self.app.processEvents()

        workspace_bounds = self.window.scene.workspace_scene_bounds()
        self.assertIsNotNone(workspace_bounds)
        self.window.view.set_zoom(0.6)
        self.window.view.centerOn(-220.0, -140.0)

        self.window.action_frame_all.trigger()
        self.app.processEvents()

        expected_all_zoom = self.window.view.fit_zoom_for_scene_rect(workspace_bounds)
        self.assertAlmostEqual(self.window.view.zoom, expected_all_zoom, places=6)
        self.assertAlmostEqual(self.window.view.center_x, workspace_bounds.center().x(), places=6)
        self.assertAlmostEqual(self.window.view.center_y, workspace_bounds.center().y(), places=6)

        self.window.scene.select_node(node_a)
        selection_bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(selection_bounds)

        self.window.action_frame_selection.trigger()
        self.app.processEvents()

        expected_selection_zoom = self.window.view.fit_zoom_for_scene_rect(selection_bounds)
        self.assertAlmostEqual(self.window.view.zoom, expected_selection_zoom, places=6)
        self.assertAlmostEqual(self.window.view.center_x, selection_bounds.center().x(), places=6)
        self.assertAlmostEqual(self.window.view.center_y, selection_bounds.center().y(), places=6)

        self.window.view.set_zoom(1.3)
        self.window.view.centerOn(900.0, -400.0)
        self.window.action_center_selection.trigger()
        self.app.processEvents()

        self.assertAlmostEqual(self.window.view.zoom, 1.3, places=6)
        self.assertAlmostEqual(self.window.view.center_x, selection_bounds.center().x(), places=6)
        self.assertAlmostEqual(self.window.view.center_y, selection_bounds.center().y(), places=6)

    def test_viewport_commands_are_noops_for_empty_graph_or_empty_selection(self) -> None:
        self.window.view.set_zoom(1.2)
        self.window.view.centerOn(55.0, -75.0)
        self.window.action_frame_all.trigger()
        self.app.processEvents()
        self.assertAlmostEqual(self.window.view.zoom, 1.2, places=6)
        self.assertAlmostEqual(self.window.view.center_x, 55.0, places=6)
        self.assertAlmostEqual(self.window.view.center_y, -75.0, places=6)

        self.window.scene.add_node_from_type("core.start", x=20.0, y=20.0)
        self.window.scene.clear_selection()
        self.window.view.set_zoom(0.9)
        self.window.view.centerOn(-25.0, 45.0)

        self.window.action_frame_selection.trigger()
        self.app.processEvents()
        self.assertAlmostEqual(self.window.view.zoom, 0.9, places=6)
        self.assertAlmostEqual(self.window.view.center_x, -25.0, places=6)
        self.assertAlmostEqual(self.window.view.center_y, 45.0, places=6)

        self.window.action_center_selection.trigger()
        self.app.processEvents()
        self.assertAlmostEqual(self.window.view.zoom, 0.9, places=6)
        self.assertAlmostEqual(self.window.view.center_x, -25.0, places=6)
        self.assertAlmostEqual(self.window.view.center_y, 45.0, places=6)


    def test_script_editor_action_focuses_editor_when_script_node_selected(self) -> None:
        script_node_id = self.window.scene.add_node_from_type("core.python_script", x=80.0, y=60.0)
        self.window.scene.focus_node(script_node_id)
        self.app.processEvents()

        self.window.action_toggle_script_editor.trigger()
        self.app.processEvents()

        self.assertTrue(self.window.script_editor.visible)
        self.assertEqual(self.window.script_editor.current_node_id, script_node_id)
        self.assertTrue(self.window.script_editor.has_focus)

    def test_multi_view_and_workspace_switch_retains_independent_camera_state(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        first_v1_id = self.window.model.project.workspaces[first_workspace_id].active_view_id

        self.window.view.set_zoom(1.4)
        self.window.view.centerOn(110.0, 210.0)
        self.app.processEvents()

        self.window._save_active_view_state()
        first_v2_id = self.window.workspace_manager.create_view(first_workspace_id, name="V2")
        self.window._restore_active_view_state()
        self.window.view.set_zoom(0.7)
        self.window.view.centerOn(-55.0, 75.0)
        first_node_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        self.app.processEvents()

        second_workspace_id = self.window.workspace_manager.create_workspace("Second")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(second_workspace_id)
        self.window.view.set_zoom(2.0)
        self.window.view.centerOn(400.0, -125.0)
        self.app.processEvents()

        self.window._switch_workspace(first_workspace_id)
        self.app.processEvents()
        self.assertEqual(
            self.window.model.project.workspaces[first_workspace_id].active_view_id,
            first_v2_id,
        )
        self.assertAlmostEqual(self.window.view.zoom, 0.7, places=2)
        self.assertAlmostEqual(self.window.view.center_x, -55.0, delta=5.0)
        self.assertAlmostEqual(self.window.view.center_y, 75.0, delta=5.0)
        self.assertIn(first_node_id, self.window.model.project.workspaces[first_workspace_id].nodes)

        self.window._switch_view(first_v1_id)
        self.app.processEvents()
        self.assertAlmostEqual(self.window.view.zoom, 1.4, places=2)
        self.assertAlmostEqual(self.window.view.center_x, 110.0, delta=5.0)
        self.assertAlmostEqual(self.window.view.center_y, 210.0, delta=5.0)

    def test_scope_navigation_updates_breadcrumbs_persists_scope_path_per_view_and_restores_runtime_camera(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        primary_view_id = workspace.active_view_id

        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        nested_node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=90.0)
        workspace.nodes[nested_node_id].parent_node_id = shell_id
        self.window.scene.refresh_workspace_from_model(workspace_id)
        self.app.processEvents()

        breadcrumbs = self.window.active_scope_breadcrumb_items
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(breadcrumbs[0]["node_id"], "")
        self.assertEqual(self.window.scene.active_scope_path, [])

        self.window.view.set_zoom(1.25)
        self.window.view.centerOn(150.0, -40.0)
        self.assertTrue(self.window.request_open_subnode_scope(shell_id))
        self.app.processEvents()

        self.assertEqual(self.window.scene.active_scope_path, [shell_id])
        self.assertEqual(workspace.views[primary_view_id].scope_path, [shell_id])
        scoped_nodes = {item["node_id"] for item in self.window.scene.nodes_model}
        self.assertIn(nested_node_id, scoped_nodes)
        self.assertNotIn(shell_id, scoped_nodes)

        self.window.view.set_zoom(0.65)
        self.window.view.centerOn(880.0, 460.0)
        self.assertTrue(self.window.request_open_scope_breadcrumb(""))
        self.app.processEvents()

        self.assertEqual(self.window.scene.active_scope_path, [])
        self.assertEqual(workspace.views[primary_view_id].scope_path, [])
        self.assertAlmostEqual(self.window.view.zoom, 1.25, places=2)
        self.assertAlmostEqual(self.window.view.center_x, 150.0, delta=5.0)
        self.assertAlmostEqual(self.window.view.center_y, -40.0, delta=5.0)

        self.assertTrue(self.window.request_open_subnode_scope(shell_id))
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_scope_path, [shell_id])
        self.assertAlmostEqual(self.window.view.zoom, 0.65, places=2)
        self.assertAlmostEqual(self.window.view.center_x, 880.0, delta=5.0)
        self.assertAlmostEqual(self.window.view.center_y, 460.0, delta=5.0)

        secondary_view_id = self.window.workspace_manager.create_view(workspace_id, name="V2")
        self.window.workspace_manager.set_active_view(workspace_id, primary_view_id)
        self.window.request_switch_view(secondary_view_id)
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_scope_path, [])
        self.assertEqual(workspace.views[secondary_view_id].scope_path, [])

        self.window.request_switch_view(primary_view_id)
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_scope_path, [shell_id])
        self.assertEqual(workspace.views[primary_view_id].scope_path, [shell_id])

    def test_qml_create_view_updates_active_view_items_and_allows_switching(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        initial_view_count = len(workspace.views)
        original_active_view_id = workspace.active_view_id
        self.window.view.set_zoom(1.7)
        self.window.view.centerOn(420.0, 315.0)

        with patch.object(
            self.window.shell_host_presenter,
            "prompt_text_value",
            return_value=("Inspection", True),
        ):
            self.window.request_create_view()
        self.app.processEvents()

        updated_workspace = self.window.model.project.workspaces[workspace_id]
        original_view = updated_workspace.views[original_active_view_id]
        active_view = updated_workspace.views[updated_workspace.active_view_id]
        self.assertEqual(len(updated_workspace.views), initial_view_count + 1)
        self.assertEqual(self.window.active_view_name, "Inspection")
        self.assertAlmostEqual(active_view.zoom, original_view.zoom, places=4)
        self.assertAlmostEqual(active_view.pan_x, original_view.pan_x, places=4)
        self.assertAlmostEqual(active_view.pan_y, original_view.pan_y, places=4)
        self.assertAlmostEqual(self.window.view.zoom_value, original_view.zoom, places=4)
        self.assertAlmostEqual(self.window.view.center_x, original_view.pan_x, places=4)
        self.assertAlmostEqual(self.window.view.center_y, original_view.pan_y, places=4)

        active_items = [item for item in self.window.active_view_items if item.get("active")]
        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0]["label"], "Inspection")
        self.assertEqual(updated_workspace.active_view_id, active_items[0]["view_id"])

        self.window.request_switch_view(original_active_view_id)
        self.app.processEvents()
        self.assertEqual(self.window.model.project.workspaces[workspace_id].active_view_id, original_active_view_id)

    def test_request_close_view_removes_target_view_and_restores_adjacent_view_state(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        original_view_id = workspace.active_view_id
        original_view = workspace.views[original_view_id]
        original_view.zoom = 1.2
        original_view.pan_x = 160.0
        original_view.pan_y = -80.0

        inspection_view_id = self.window.workspace_manager.create_view(workspace_id, name="Inspection")
        inspection_view = workspace.views[inspection_view_id]
        inspection_view.zoom = 1.85
        inspection_view.pan_x = 540.0
        inspection_view.pan_y = 260.0
        self.window.request_switch_view(inspection_view_id)
        self.app.processEvents()

        closed = self.window.request_close_view(inspection_view_id)
        self.app.processEvents()

        self.assertTrue(closed)
        self.assertNotIn(inspection_view_id, workspace.views)
        self.assertEqual(workspace.active_view_id, original_view_id)
        self.assertAlmostEqual(self.window.view.zoom_value, original_view.zoom, places=4)
        self.assertAlmostEqual(self.window.view.center_x, original_view.pan_x, places=4)
        self.assertAlmostEqual(self.window.view.center_y, original_view.pan_y, places=4)

    def test_request_rename_view_updates_active_view_labels(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        view_id = self.window.workspace_manager.create_view(workspace_id, name="Inspection")
        self.app.processEvents()

        with patch.object(
            self.window.shell_host_presenter,
            "prompt_text_value",
            return_value=("Inspection Renamed", True),
        ):
            renamed = self.window.request_rename_view(view_id)
        self.app.processEvents()

        self.assertTrue(renamed)
        self.assertEqual(workspace.views[view_id].name, "Inspection Renamed")
        active_items = [item for item in self.window.active_view_items if item.get("view_id") == view_id]
        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0]["label"], "Inspection Renamed")
        self.assertEqual(self.window.active_view_name, "Inspection Renamed")

    def test_request_move_view_tab_reorders_active_view_items(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        first_view_id = workspace.active_view_id
        second_view_id = self.window.workspace_manager.create_view(workspace_id, name="Inspection")
        third_view_id = self.window.workspace_manager.create_view(workspace_id, name="Review")
        self.app.processEvents()

        moved = self.window.request_move_view_tab(2, 0)
        self.app.processEvents()

        self.assertTrue(moved)
        self.assertEqual(list(workspace.views), [third_view_id, first_view_id, second_view_id])
        self.assertEqual(
            [item["view_id"] for item in self.window.active_view_items],
            [third_view_id, first_view_id, second_view_id],
        )
        self.assertEqual(workspace.active_view_id, third_view_id)

    def test_request_close_view_rejects_last_remaining_view(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        only_view_id = workspace.active_view_id

        with patch.object(QMessageBox, "warning") as warning_mock:
            closed = self.window.request_close_view(only_view_id)

        self.assertFalse(closed)
        self.assertIn(only_view_id, workspace.views)
        warning_mock.assert_called_once()

    def test_closing_dirty_workspace_honors_unsaved_warning(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.workspace_manager.create_workspace("Second")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(first_workspace_id)
        self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        self.app.processEvents()

        first_index = -1
        for index in range(self.window.workspace_tabs.count()):
            if self.window.workspace_tabs.tabData(index) == first_workspace_id:
                first_index = index
                break
        self.assertGreaterEqual(first_index, 0)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window._on_workspace_tab_close(first_index)
        self.assertIn(first_workspace_id, self.window.model.project.workspaces)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.window._on_workspace_tab_close(first_index)
        self.assertNotIn(first_workspace_id, self.window.model.project.workspaces)

    def test_request_move_workspace_tab_reorders_workspace_tabs(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        second_workspace_id = self.window.workspace_manager.create_workspace("Second")
        third_workspace_id = self.window.workspace_manager.create_workspace("Third")
        self.window._refresh_workspace_tabs()
        self.app.processEvents()

        moved = self.window.request_move_workspace_tab(2, 0)
        self.app.processEvents()

        self.assertTrue(moved)
        self.assertEqual(
            [self.window.workspace_tabs.tabData(index) for index in range(self.window.workspace_tabs.count())],
            [third_workspace_id, first_workspace_id, second_workspace_id],
        )
        self.assertEqual(self.window.workspace_manager.active_workspace_id(), third_workspace_id)

    def test_qml_workspace_tabs_allow_leftward_drag_from_non_leftmost_slots(self) -> None:
        self.window.workspace_manager.create_workspace("Second")
        self.window.workspace_manager.create_workspace("Third")
        self.window._refresh_workspace_tabs()

        strip = self._inspector_object("workspaceControlsStrip")

        def ordered_tab_slots() -> list[QObject]:
            slots = strip.property("tabSlots")
            if isinstance(slots, QJSValue):
                slots = slots.toVariant()
            return sorted(slots or [], key=lambda slot: float(slot.property("x")))

        def drag_bounds_ready() -> bool:
            slots = ordered_tab_slots()
            if len(slots) < 3:
                return False
            return (
                float(slots[1].property("dragMinimumX")) < 0.0
                and float(slots[2].property("dragMinimumX")) < 0.0
                and float(slots[1].property("dragMaximumX")) > 0.0
            )

        wait_for_condition_or_raise(
            drag_bounds_ready,
            timeout_ms=150,
            poll_interval_ms=10,
            app=self.app,
            timeout_message="Timed out waiting for workspace tab drag bounds to settle.",
        )

        slots = ordered_tab_slots()
        self.assertGreaterEqual(len(slots), 3)
        self.assertAlmostEqual(float(slots[0].property("dragMinimumX")), 0.0, places=4)
        self.assertLess(float(slots[1].property("dragMinimumX")), 0.0)
        self.assertLess(float(slots[2].property("dragMinimumX")), 0.0)
        self.assertGreater(float(slots[1].property("dragMaximumX")), 0.0)

    def test_qml_workspace_tabs_chevrons_scroll_overflowed_strip_and_keep_create_visible(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        for index in range(8):
            self.window.workspace_manager.create_workspace(
                f"Overflow Workspace {index} - Static Displacement Viewer"
            )
        self.window._refresh_workspace_tabs()
        self.app.processEvents()

        strip = self._inspector_object("workspaceControlsStrip")
        backward_button = self._strip_child(strip, "tabStripScrollBackwardButton")
        forward_button = self._strip_child(strip, "tabStripScrollForwardButton")
        create_button = self._strip_child(strip, "tabStripCreateButton")

        wait_for_condition_or_raise(
            lambda: bool(strip.property("tabsOverflowActive")),
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not overflow for chevron test.",
        )

        self.window.workspace_tabs.activate_workspace(first_workspace_id)
        self.app.processEvents()
        wait_for_condition_or_raise(
            lambda: float(strip.property("tabsContentX")) <= 0.5,
            timeout_ms=800,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not return to the left edge.",
        )

        self.assertTrue(bool(create_button.property("visible")))
        self.assertTrue(bool(forward_button.property("visible")))
        QMetaObject.invokeMethod(
            forward_button,
            "click",
            Qt.ConnectionType.DirectConnection,
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: float(strip.property("tabsContentX")) > 0.5,
            timeout_ms=800,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not scroll right after chevron click.",
        )

        self.assertTrue(bool(create_button.property("visible")))
        self.assertTrue(bool(backward_button.property("enabled")))

        QMetaObject.invokeMethod(
            backward_button,
            "click",
            Qt.ConnectionType.DirectConnection,
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: float(strip.property("tabsContentX")) <= 0.5,
            timeout_ms=800,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not scroll back left after chevron click.",
        )

    def test_qml_workspace_tabs_shift_wheel_and_horizontal_delta_scroll_only_when_supported(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        for index in range(8):
            self.window.workspace_manager.create_workspace(
                f"Wheel Workspace {index} - Static Stress Norm Export"
            )
        self.window._refresh_workspace_tabs()
        self.app.processEvents()

        strip = self._inspector_object("workspaceControlsStrip")
        wait_for_condition_or_raise(
            lambda: bool(strip.property("tabsOverflowActive")),
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not overflow for wheel test.",
        )

        self.window.workspace_tabs.activate_workspace(first_workspace_id)
        self.app.processEvents()
        wait_for_condition_or_raise(
            lambda: float(strip.property("tabsContentX")) <= 0.5,
            timeout_ms=800,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not return to the left edge before wheel assertions.",
        )

        strip.setProperty("testWheelHorizontalDelta", 0)
        strip.setProperty("testWheelVerticalDelta", -120)
        strip.setProperty("testWheelShiftHeld", False)
        QMetaObject.invokeMethod(
            strip,
            "applyConfiguredTestWheelScroll",
            Qt.ConnectionType.DirectConnection,
        )
        self.app.processEvents()
        self.assertAlmostEqual(float(strip.property("tabsContentX")), 0.0, places=4)

        strip.setProperty("testWheelShiftHeld", True)
        QMetaObject.invokeMethod(
            strip,
            "applyConfiguredTestWheelScroll",
            Qt.ConnectionType.DirectConnection,
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: float(strip.property("tabsContentX")) > 0.5,
            timeout_ms=800,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Shift+wheel did not scroll the overflowed workspace strip.",
        )
        shift_scroll_x = float(strip.property("tabsContentX"))

        strip.setProperty("testWheelHorizontalDelta", -120)
        strip.setProperty("testWheelVerticalDelta", 0)
        strip.setProperty("testWheelShiftHeld", False)
        QMetaObject.invokeMethod(
            strip,
            "applyConfiguredTestWheelScroll",
            Qt.ConnectionType.DirectConnection,
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: float(strip.property("tabsContentX")) > shift_scroll_x + 0.5,
            timeout_ms=800,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Native horizontal delta did not scroll the overflowed workspace strip.",
        )

    def test_qml_workspace_tabs_auto_reveal_active_workspace_when_selection_moves_offscreen(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        created_workspace_ids: list[str] = []
        for index in range(8):
            created_workspace_ids.append(
                self.window.workspace_manager.create_workspace(
                    f"Reveal Workspace {index} - Static Displacement Viewer"
                )
            )
        self.window._refresh_workspace_tabs()
        self.app.processEvents()

        strip = self._inspector_object("workspaceControlsStrip")
        wait_for_condition_or_raise(
            lambda: bool(strip.property("tabsOverflowActive")),
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not overflow for auto-reveal test.",
        )

        self.window.workspace_tabs.activate_workspace(first_workspace_id)
        self.app.processEvents()
        wait_for_condition_or_raise(
            lambda: float(strip.property("tabsContentX")) <= 0.5,
            timeout_ms=800,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not reveal the leftmost active tab.",
        )

        last_workspace_id = created_workspace_ids[-1]
        self.window.workspace_tabs.activate_workspace(last_workspace_id)
        self.app.processEvents()
        wait_for_condition_or_raise(
            lambda: self._tab_slot_fully_visible(strip, self._active_tab_slot(strip)),
            timeout_ms=1200,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not scroll to reveal the last workspace.",
        )

        active_slot = self._active_tab_slot(strip)
        self.assertTrue(self._tab_slot_fully_visible(strip, active_slot))

        self.window.workspace_tabs.activate_workspace(first_workspace_id)
        self.app.processEvents()
        wait_for_condition_or_raise(
            lambda: self._tab_slot_fully_visible(strip, self._active_tab_slot(strip)),
            timeout_ms=1200,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Workspace strip did not scroll back to reveal the first workspace.",
        )

        active_slot = self._active_tab_slot(strip)
        self.assertTrue(self._tab_slot_fully_visible(strip, active_slot))
