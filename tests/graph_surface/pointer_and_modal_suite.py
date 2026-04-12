from __future__ import annotations

from tests.graph_surface.environment import *  # noqa: F403

pytestmark = pytest.mark.xdist_group("p03_graph_surface")  # noqa: F405

class GraphSurfaceInputContractTests(GraphSurfaceInputContractTestBase):
    def test_graph_surface_pointer_audit_rejects_hover_proxy_shims_and_untracked_surface_mouse_areas(self) -> None:
        failures = self._graph_surface_pointer_audit_failures_with_fallback()
        if failures:
            self.fail("\n\n".join(failures))

    def test_surface_loader_forwards_embedded_interactive_rects_for_inline_properties(self) -> None:
        self._run_qml_probe(
            "loader-embedded-rects",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))

            assert len(embedded_rects) == 1
            assert rect_field(embedded_rects[0], "x") > 80.0
            assert rect_field(embedded_rects[0], "y") >= 30.0
            assert rect_field(embedded_rects[0], "width") > 80.0
            assert rect_field(embedded_rects[0], "width") < 120.0
            assert rect_field(embedded_rects[0], "height") >= 18.0
            """,
        )

    def test_surface_loader_tracks_control_scoped_rects_for_all_core_inline_editors(self) -> None:
        self._run_qml_probe(
            "loader-core-inline-editor-rects",
            """
            payload = node_payload()
            payload["inline_properties"] = [
                {
                    "key": "enabled",
                    "label": "Enabled",
                    "inline_editor": "toggle",
                    "value": True,
                    "overridden_by_input": False,
                    "input_port_label": "enabled",
                },
                {
                    "key": "mode",
                    "label": "Mode",
                    "inline_editor": "enum",
                    "value": "two",
                    "enum_values": ["one", "two", "three"],
                    "overridden_by_input": False,
                    "input_port_label": "mode",
                },
                {
                    "key": "message",
                    "label": "Message",
                    "inline_editor": "text",
                    "value": "log message",
                    "overridden_by_input": False,
                    "input_port_label": "message",
                },
                {
                    "key": "count",
                    "label": "Count",
                    "inline_editor": "number",
                    "value": "5",
                    "overridden_by_input": False,
                    "input_port_label": "count",
                },
            ]

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
            assert len(embedded_rects) == 4

            xs = [rect_field(rect, "x") for rect in embedded_rects]
            widths = [rect_field(rect, "width") for rect in embedded_rects]
            ys = [rect_field(rect, "y") for rect in embedded_rects]

            assert all(x > 80.0 for x in xs)
            assert widths[0] < 40.0
            assert all(width > 80.0 for width in widths[1:])
            assert ys == sorted(ys)
            """,
        )

    def test_host_body_interactions_yield_inside_embedded_rects_but_still_work_adjacent_to_them(self) -> None:
        self._run_qml_probe(
            "embedded-rect-hit-testing",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            gesture_layer = host.findChild(QObject, "graphNodeHostGestureLayer")
            drag_area = host.findChild(QObject, "graphNodeDragArea")
            assert loader is not None
            assert gesture_layer is not None
            assert drag_area is not None
            assert drag_area.parentItem().objectName() == "graphNodeHostGestureLayer"

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
            assert len(embedded_rects) == 1
            row_rect = embedded_rects[0]
            assert rect_field(row_rect, "x") > 80.0

            window = attach_host_to_window(host)

            inside_point = host_scene_point(
                host,
                rect_field(row_rect, "x") + 8.0,
                rect_field(row_rect, "y") + rect_field(row_rect, "height") * 0.5,
            )
            body_local_x = rect_field(row_rect, "x") - 8.0
            body_local_y = rect_field(row_rect, "y") + rect_field(row_rect, "height") * 0.5
            body_point = host_scene_point(host, body_local_x, body_local_y)

            assert_host_pointer_routing(
                host,
                window,
                inside_point,
                body_point,
                "node_surface_contract_test",
                expected_body_local=(body_local_x, body_local_y),
            )

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_deactivates_far_offscreen_node_surfaces_but_keeps_force_active_exceptions(self) -> None:
        self._run_qml_probe(
            "graph-canvas-offscreen-render-activation",
            """
            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            def node_card_for(node_id):
                for item in named_child_items(canvas, "graphNodeCard"):
                    node_data = variant_value(item.property("nodeData")) or {}
                    if str(node_data.get("node_id", "")) == str(node_id):
                        return item
                raise AssertionError(f"Missing node card for {node_id!r}")

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id

            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)

            padded_node_id = scene.add_node_from_type("core.logger", 340.0, 40.0)
            offscreen_node_id = scene.add_node_from_type("core.logger", 900.0, 620.0)
            scene.clear_selection()

            view = ViewportBridge()
            view.set_viewport_size(640.0, 480.0)
            view.set_view_state(1.0, 0.0, 0.0)
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                scene_bridge=scene,
                view_bridge=view,
            )

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )
            settle_events(3)

            padded_card = node_card_for(padded_node_id)
            offscreen_card = node_card_for(offscreen_node_id)
            padded_loader = padded_card.findChild(QObject, "graphNodeSurfaceLoader")
            offscreen_loader = offscreen_card.findChild(QObject, "graphNodeSurfaceLoader")

            assert padded_loader is not None
            assert offscreen_loader is not None
            assert bool(padded_card.property("renderActive"))
            assert bool(padded_loader.property("renderActive"))
            assert bool(padded_loader.property("surfaceLoaded"))
            assert not bool(offscreen_card.property("renderActive"))
            assert not bool(offscreen_loader.property("renderActive"))
            assert not bool(offscreen_loader.property("surfaceLoaded"))

            scene.select_node(offscreen_node_id, False)
            settle_events(2)

            assert bool(offscreen_card.property("renderActive"))
            assert bool(offscreen_loader.property("renderActive"))
            assert bool(offscreen_loader.property("surfaceLoaded"))

            scene.clear_selection()
            settle_events(2)

            assert not bool(offscreen_card.property("renderActive"))
            assert not bool(offscreen_loader.property("renderActive"))
            assert not bool(offscreen_loader.property("surfaceLoaded"))

            canvas.setProperty(
                "pendingConnectionPort",
                {"node_id": offscreen_node_id, "port_key": "exec_in", "direction": "in"},
            )
            settle_events(2)

            assert bool(offscreen_card.property("renderActive"))
            assert bool(offscreen_loader.property("surfaceLoaded"))

            canvas.setProperty("pendingConnectionPort", None)
            settle_events(2)

            assert not bool(offscreen_card.property("renderActive"))
            assert not bool(offscreen_loader.property("surfaceLoaded"))

            canvas.setProperty(
                "dropPreviewPort",
                {"node_id": offscreen_node_id, "port_key": "exec_in", "direction": "in"},
            )
            settle_events(2)

            assert bool(offscreen_card.property("renderActive"))
            assert bool(offscreen_loader.property("surfaceLoaded"))

            canvas.setProperty("dropPreviewPort", None)
            settle_events(2)

            assert not bool(offscreen_card.property("renderActive"))
            assert not bool(offscreen_loader.property("surfaceLoaded"))

            canvas.setProperty("nodeContextNodeId", offscreen_node_id)
            settle_events(2)

            assert bool(offscreen_card.property("renderActive"))
            assert bool(offscreen_loader.property("surfaceLoaded"))

            canvas.setProperty("nodeContextNodeId", "")
            settle_events(2)

            assert not bool(offscreen_card.property("renderActive"))
            assert not bool(offscreen_loader.property("surfaceLoaded"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_pendingConnectionPort_request_connect_ports_preserves_flowchart_gesture_order(self) -> None:
        self._run_qml_probe(
            "graph-canvas-flowchart-gesture-order",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSlot

            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui.graph_interactions import GraphInteractions
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            class FlowchartShellBridgeStub(QObject):
                def __init__(self, interactions):
                    super().__init__()
                    self._interactions = interactions
                    self.connect_calls = []

                @pyqtProperty(bool, constant=True)
                def graphics_minimap_expanded(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, constant=True)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, constant=True)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, constant=True)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(str, constant=True)
                def graphics_performance_mode(self):
                    return "full_fidelity"

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                @pyqtSlot(str, str, str, str, result=bool)
                def request_connect_ports(self, node_a_id, port_a, node_b_id, port_b):
                    request = (
                        str(node_a_id or ""),
                        str(port_a or ""),
                        str(node_b_id or ""),
                        str(port_b or ""),
                    )
                    self.connect_calls.append(request)
                    result = self._interactions.connect_ports(*request)
                    return bool(result.ok)

            model = GraphModel()
            registry = build_default_registry()
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, model.active_workspace.workspace_id)
            interactions = GraphInteractions(scene, registry)
            shell_bridge = FlowchartShellBridgeStub(interactions)
            view = ViewportBridge()
            view.set_viewport_size(640.0, 480.0)
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=shell_bridge,
                scene_bridge=scene,
                view_bridge=view,
            )

            first_source_id = scene.add_node_from_type("passive.flowchart.process", 20.0, 20.0)
            first_target_id = scene.add_node_from_type("passive.flowchart.process", 360.0, 160.0)
            second_source_id = scene.add_node_from_type("passive.flowchart.process", 720.0, 40.0)
            second_target_id = scene.add_node_from_type("passive.flowchart.process", 1060.0, 180.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )

            canvas.handlePortClick(first_source_id, "right", "neutral", 120.0, 90.0)
            app.processEvents()

            pending = variant_value(canvas.property("pendingConnectionPort"))
            assert pending is not None
            assert pending["direction"] == "neutral"
            assert pending["origin_side"] == "right"

            canvas.handlePortClick(first_target_id, "top", "neutral", 460.0, 200.0)
            app.processEvents()

            assert shell_bridge.connect_calls[0] == (
                first_source_id,
                "right",
                first_target_id,
                "top",
            )
            assert canvas.property("pendingConnectionPort") is None

            canvas.handlePortClick(second_target_id, "left", "neutral", 1160.0, 230.0)
            app.processEvents()

            pending = variant_value(canvas.property("pendingConnectionPort"))
            assert pending is not None
            assert pending["direction"] == "neutral"
            assert pending["origin_side"] == "left"

            canvas.handlePortClick(second_source_id, "bottom", "neutral", 820.0, 150.0)
            app.processEvents()

            assert shell_bridge.connect_calls[1] == (
                second_target_id,
                "left",
                second_source_id,
                "bottom",
            )

            workspace = model.active_workspace
            stored_edges = {
                (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key)
                for edge in workspace.edges.values()
            }
            assert (
                first_source_id,
                "right",
                first_target_id,
                "top",
            ) in stored_edges
            assert (
                second_target_id,
                "left",
                second_source_id,
                "bottom",
            ) in stored_edges

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_pendingConnectionPort_rejects_same_node_logic_flow_edge(self) -> None:
        self._run_qml_probe_with_retry(
            "graph-canvas-same-node-logic-flow-rejected",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSlot

            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            class FlowShellBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.connect_calls = []

                @pyqtProperty(bool, constant=True)
                def graphics_minimap_expanded(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, constant=True)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, constant=True)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, constant=True)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(str, constant=True)
                def graphics_performance_mode(self):
                    return "full_fidelity"

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                @pyqtSlot(str, str, str, str, result=bool)
                def request_connect_ports(self, node_a_id, port_a, node_b_id, port_b):
                    self.connect_calls.append(
                        (
                            str(node_a_id or ""),
                            str(port_a or ""),
                            str(node_b_id or ""),
                            str(port_b or ""),
                        )
                    )
                    return True

            model = GraphModel()
            registry = build_default_registry()
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, model.active_workspace.workspace_id)
            shell_bridge = FlowShellBridgeStub()
            view = ViewportBridge()
            view.set_viewport_size(640.0, 480.0)
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=shell_bridge,
                scene_bridge=scene,
                view_bridge=view,
            )

            node_id = scene.add_node_from_type("core.logger", 20.0, 20.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )

            canvas.handlePortClick(node_id, "exec_in", "in", 40.0, 84.0)
            app.processEvents()

            pending = variant_value(canvas.property("pendingConnectionPort"))
            assert pending is not None
            assert pending["node_id"] == node_id
            assert pending["port_key"] == "exec_in"

            canvas.handlePortClick(node_id, "exec_out", "out", 220.0, 84.0)
            app.processEvents()

            assert shell_bridge.connect_calls == []
            pending = variant_value(canvas.property("pendingConnectionPort"))
            assert pending is not None
            assert pending["node_id"] == node_id
            assert pending["port_key"] == "exec_in"

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_projects_active_view_hide_filters_and_ctrl_double_click_keeps_plain_quick_insert(self) -> None:
        self._run_qml_probe(
            "graph-canvas-hide-filter-projection-and-ctrl-double-click",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSlot
            from PyQt6.QtTest import QTest

            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            class CanvasShellBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.quick_insert_calls = []

                @pyqtProperty(bool, constant=True)
                def graphics_minimap_expanded(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(str, constant=True)
                def graphics_grid_style(self):
                    return "lines"

                @pyqtProperty(str, constant=True)
                def graphics_edge_crossing_style(self):
                    return "none"

                @pyqtProperty(bool, constant=True)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_port_labels(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, constant=True)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, constant=True)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, constant=True)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(str, constant=True)
                def graphics_performance_mode(self):
                    return "full_fidelity"

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                @pyqtSlot(float, float, float, float)
                def request_open_canvas_quick_insert(self, scene_x, scene_y, overlay_x, overlay_y):
                    self.quick_insert_calls.append(
                        (
                            float(scene_x),
                            float(scene_y),
                            float(overlay_x),
                            float(overlay_y),
                        )
                    )

            model = GraphModel()
            registry = build_default_registry()
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, model.active_workspace.workspace_id)
            view = ViewportBridge()
            view.set_viewport_size(640.0, 480.0)
            shell_bridge = CanvasShellBridgeStub()
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=shell_bridge,
                scene_bridge=scene,
                view_bridge=view,
            )

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )
            window = attach_host_to_window(canvas, width=640, height=480)

            try:
                input_layers = canvas.findChild(QObject, "graphCanvasInputLayers")
                marquee_area = canvas.findChild(QObject, "graphCanvasMarqueeArea")
                assert input_layers is not None
                assert marquee_area is not None
                assert not bool(canvas.property("hideLockedPorts"))
                assert not bool(canvas.property("hideOptionalPorts"))

                scene.set_hide_locked_ports(True)
                settle_events(3)
                assert bool(canvas.property("hideLockedPorts"))
                assert not bool(canvas.property("hideOptionalPorts"))

                scene.set_hide_optional_ports(True)
                settle_events(3)
                assert bool(canvas.property("hideOptionalPorts"))

                point = QPoint(160, 120)
                QTest.mouseDClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, point)
                settle_events(3)

                assert not bool(canvas.property("hideLockedPorts"))
                assert bool(canvas.property("hideOptionalPorts"))
                assert shell_bridge.quick_insert_calls == []

                QTest.mouseDClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
                settle_events(3)

                assert len(shell_bridge.quick_insert_calls) == 1
                assert not bool(canvas.property("hideLockedPorts"))
                assert bool(canvas.property("hideOptionalPorts"))
            finally:
                dispose_host_window(canvas, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_graph_canvas_middle_button_chords_toggle_hide_filters_without_pan_or_box_zoom(self) -> None:
        self._run_qml_probe(
            "graph-canvas-hide-filter-middle-button-chords",
            """
            from PyQt6.QtCore import QObject, pyqtProperty
            from PyQt6.QtTest import QTest

            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            class CanvasShellBridgeStub(QObject):
                @pyqtProperty(bool, constant=True)
                def graphics_minimap_expanded(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(str, constant=True)
                def graphics_grid_style(self):
                    return "lines"

                @pyqtProperty(str, constant=True)
                def graphics_edge_crossing_style(self):
                    return "none"

                @pyqtProperty(bool, constant=True)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_port_labels(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, constant=True)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, constant=True)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, constant=True)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(str, constant=True)
                def graphics_performance_mode(self):
                    return "full_fidelity"

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

            model = GraphModel()
            registry = build_default_registry()
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, model.active_workspace.workspace_id)
            view = ViewportBridge()
            view.set_viewport_size(640.0, 480.0)
            view.set_view_state(1.0, 0.0, 0.0)
            shell_bridge = CanvasShellBridgeStub()
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=shell_bridge,
                scene_bridge=scene,
                view_bridge=view,
            )

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )
            window = attach_host_to_window(canvas, width=640, height=480)

            try:
                pan_area = canvas.findChild(QObject, "graphCanvasPanArea")
                marquee_area = canvas.findChild(QObject, "graphCanvasMarqueeArea")
                assert pan_area is not None
                assert marquee_area is not None

                baseline_zoom = float(view.zoom_value)
                baseline_center_x = float(view.center_x)
                baseline_center_y = float(view.center_y)

                left_point = QPoint(180, 160)
                right_point = QPoint(240, 220)

                QTest.mousePress(window, Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.NoModifier, left_point)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, left_point)
                settle_events(3)
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, left_point)
                QTest.mouseRelease(window, Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.NoModifier, left_point)
                settle_events(3)

                assert bool(canvas.property("hideLockedPorts"))
                assert not bool(canvas.property("hideOptionalPorts"))

                QTest.mousePress(window, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, right_point)
                QTest.mousePress(window, Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.NoModifier, right_point)
                settle_events(3)
                QTest.mouseRelease(window, Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.NoModifier, right_point)
                QTest.mouseRelease(window, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, right_point)
                settle_events(3)

                assert bool(canvas.property("hideLockedPorts"))
                assert bool(canvas.property("hideOptionalPorts"))
                assert not bool(marquee_area.property("selecting"))
                assert not bool(pan_area.property("panning"))
                assert float(view.zoom_value) == baseline_zoom
                assert float(view.center_x) == baseline_center_x
                assert float(view.center_y) == baseline_center_y
            finally:
                dispose_host_window(canvas, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )
