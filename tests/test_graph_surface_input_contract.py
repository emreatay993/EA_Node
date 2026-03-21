from __future__ import annotations

from pathlib import Path
import textwrap
import unittest
from unittest.mock import patch

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    assert_no_graph_surface_pointer_regressions,
    run_qml_probe,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


class _RenderQualityPayloadPlugin:
    def __init__(self, spec: NodeTypeSpec) -> None:
        self._spec = spec

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, _ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult()


class GraphSurfaceInputContractTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl, pyqtProperty
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.ui.media_preview_provider import (
                LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
                LocalMediaPreviewImageProvider,
            )

            class ThemeBridgeStub(QObject):
                @pyqtProperty("QVariantMap", constant=True)
                def palette(self):
                    return {
                        "accent": "#2F89FF",
                        "border": "#3a4355",
                        "canvas_bg": "#151821",
                        "canvas_major_grid": "#2f3644",
                        "canvas_minor_grid": "#222833",
                        "group_title_fg": "#d5dbea",
                        "hover": "#33405c",
                        "muted_fg": "#95a0b8",
                        "panel_bg": "#1b1f2a",
                        "panel_title_fg": "#eef3ff",
                        "pressed": "#22304a",
                        "toolbar_bg": "#202635",
                    }

            class GraphThemeBridgeStub(QObject):
                @pyqtProperty("QVariantMap", constant=True)
                def node_palette(self):
                    return {
                        "card_bg": "#1f2431",
                        "card_border": "#414a5d",
                        "card_selected_border": "#5da9ff",
                        "header_bg": "#252c3c",
                        "header_fg": "#eef3ff",
                        "inline_driven_fg": "#aeb8ce",
                        "inline_input_bg": "#18202d",
                        "inline_input_border": "#465066",
                        "inline_input_fg": "#eef3ff",
                        "inline_label_fg": "#d5dbea",
                        "inline_row_bg": "#202635",
                        "inline_row_border": "#3a4355",
                        "port_interactive_border": "#8ca0c7",
                        "port_interactive_fill": "#101521",
                        "port_interactive_ring_border": "#7fb2ff",
                        "port_interactive_ring_fill": "#1a2233",
                        "port_label_fg": "#d5dbea",
                        "scope_badge_bg": "#1f3657",
                        "scope_badge_border": "#4c7bc0",
                        "scope_badge_fg": "#eef3ff",
                    }

                @pyqtProperty("QVariantMap", constant=True)
                def port_kind_palette(self):
                    return {
                        "data": "#7AA8FF",
                        "exec": "#67D487",
                        "completed": "#E4CE7D",
                        "failed": "#D94F4F",
                    }

                @pyqtProperty("QVariantMap", constant=True)
                def edge_palette(self):
                    return {
                        "invalid_drag_stroke": "#D94F4F",
                        "preview_stroke": "#95a0b8",
                        "selected_stroke": "#5da9ff",
                        "valid_drag_stroke": "#67D487",
                    }

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())
            engine.rootContext().setContextProperty("themeBridge", ThemeBridgeStub())
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridgeStub())

            repo_root = Path.cwd()
            components_dir = repo_root / "ea_node_editor" / "ui_qml" / "components"
            graph_canvas_qml_path = components_dir / "GraphCanvas.qml"
            graph_node_host_qml_path = components_dir / "graph" / "GraphNodeHost.qml"

            def create_component(path, initial_properties):
                component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
                if component.status() != QQmlComponent.Status.Ready:
                    errors = "\\n".join(error.toString() for error in component.errors())
                    raise AssertionError(f"Failed to load {path.name}:\\n{errors}")
                if hasattr(component, "createWithInitialProperties"):
                    obj = component.createWithInitialProperties(initial_properties)
                else:
                    obj = component.create()
                    for key, value in initial_properties.items():
                        obj.setProperty(key, value)
                if obj is None:
                    errors = "\\n".join(error.toString() for error in component.errors())
                    raise AssertionError(f"Failed to instantiate {path.name}:\\n{errors}")
                app.processEvents()
                return obj

            def node_payload(surface_family="standard", surface_variant=""):
                return {
                    "node_id": "node_surface_contract_test",
                    "type_id": "core.logger",
                    "title": "Logger",
                    "x": 120.0,
                    "y": 120.0,
                    "width": 210.0,
                    "height": 88.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "active",
                    "surface_family": surface_family,
                    "surface_variant": surface_variant,
                    "surface_metrics": {
                        "default_width": 210.0,
                        "default_height": 88.0,
                        "min_width": 120.0,
                        "min_height": 50.0,
                        "collapsed_width": 130.0,
                        "collapsed_height": 36.0,
                        "header_height": 24.0,
                        "header_top_margin": 4.0,
                        "body_left_margin": 8.0,
                        "body_right_margin": 8.0,
                        "body_top": 30.0,
                        "body_height": 30.0,
                        "port_top": 60.0,
                        "port_height": 18.0,
                        "port_center_offset": 6.0,
                        "port_side_margin": 8.0,
                        "port_dot_radius": 3.5,
                        "resize_handle_size": 16.0,
                    },
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [
                        {
                            "key": "exec_in",
                            "label": "Exec In",
                            "direction": "in",
                            "kind": "exec",
                            "data_type": "exec",
                            "connected": False,
                        },
                        {
                            "key": "exec_out",
                            "label": "Exec Out",
                            "direction": "out",
                            "kind": "exec",
                            "data_type": "exec",
                            "connected": False,
                        },
                    ],
                    "inline_properties": [
                        {
                            "key": "message",
                            "label": "Message",
                            "inline_editor": "text",
                            "value": "log message",
                            "overridden_by_input": False,
                            "input_port_label": "message",
                        }
                    ],
                }
            """,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

    def test_graph_surface_pointer_audit_rejects_hover_proxy_shims_and_untracked_surface_mouse_areas(self) -> None:
        assert_no_graph_surface_pointer_regressions(self)

    def test_graph_scene_payload_builder_publishes_normalized_render_quality_metadata(self) -> None:
        registry: NodeRegistry = build_default_registry()
        spec = NodeTypeSpec(
            type_id="tests.render_quality_payload",
            display_name="Render Quality Payload",
            category="Tests",
            icon="",
            ports=(),
            properties=(),
            render_quality={
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            },  # type: ignore[arg-type]
        )
        registry.register(lambda: _RenderQualityPayloadPlugin(spec))

        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(
            workspace_id,
            spec.type_id,
            spec.display_name,
            80.0,
            120.0,
        )

        builder = GraphScenePayloadBuilder()
        nodes_payload, _minimap_payload, _edges_payload = builder.rebuild_models(
            model=model,
            registry=registry,
            workspace_id=workspace_id,
            scope_path=(),
            graph_theme_bridge=None,
        )

        payload = next(item for item in nodes_payload if item["type_id"] == spec.type_id)
        self.assertEqual(
            payload["render_quality"],
            {
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            },
        )

    def test_graph_node_host_render_quality_contract_exposes_reduced_quality_tier(self) -> None:
        self._run_qml_probe(
            "host-render-quality-contract",
            """
            payload = node_payload()
            payload["render_quality"] = {
                "weight_class": "heavy",
                "max_performance_strategy": "generic_fallback",
                "supported_quality_tiers": ["full", "reduced"],
            }

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "snapshotReuseActive": True,
                    "shadowSimplificationActive": True,
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeStandardSurface")
            assert loader is not None
            assert surface is not None

            render_quality = variant_value(host.property("renderQuality"))
            loader_render_quality = variant_value(loader.property("renderQuality"))
            context = variant_value(host.property("surfaceQualityContext"))
            loader_context = variant_value(loader.property("surfaceQualityContext"))

            assert render_quality == {
                "weight_class": "heavy",
                "max_performance_strategy": "generic_fallback",
                "supported_quality_tiers": ["full", "reduced"],
            }
            assert loader_render_quality == render_quality
            assert host.property("requestedQualityTier") == "reduced"
            assert host.property("resolvedQualityTier") == "reduced"
            assert not bool(host.property("proxySurfaceRequested"))
            assert loader.property("requestedQualityTier") == "reduced"
            assert loader.property("resolvedQualityTier") == "reduced"
            assert not bool(loader.property("proxySurfaceRequested"))
            assert not bool(loader.property("proxySurfaceActive"))
            assert context["requested_quality_tier"] == "reduced"
            assert context["resolved_quality_tier"] == "reduced"
            assert not bool(context["proxy_surface_requested"])
            assert loader_context["resolved_quality_tier"] == "reduced"
            assert surface.property("host").property("resolvedQualityTier") == "reduced"
            """,
        )

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

    def test_graph_canvas_routes_surface_control_edits_by_explicit_node_id(self) -> None:
        self._run_qml_probe(
            "graph-canvas-surface-control-bridge",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

            class SceneBridgeStub(QObject):
                nodes_changed = pyqtSignal()
                edges_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.set_node_property_calls = []
                    self._nodes_model = [node_payload()]
                    self._selected_node_lookup = {}

                @pyqtProperty("QVariantList", notify=nodes_changed)
                def nodes_model(self):
                    return self._nodes_model

                @pyqtProperty("QVariantList", notify=edges_changed)
                def edges_model(self):
                    return []

                @pyqtProperty("QVariantMap", notify=nodes_changed)
                def selected_node_lookup(self):
                    return self._selected_node_lookup

                @pyqtSlot(str)
                @pyqtSlot(str, bool)
                def select_node(self, node_id, additive=False):
                    normalized_node_id = str(node_id or "")
                    self.select_calls.append((normalized_node_id, bool(additive)))
                    self._selected_node_lookup = {normalized_node_id: True} if normalized_node_id else {}
                    self.nodes_changed.emit()

                @pyqtSlot(str, str, "QVariant")
                def set_node_property(self, node_id, key, value):
                    self.set_node_property_calls.append((str(node_id or ""), str(key or ""), variant_value(value)))

                @pyqtSlot(str, str, str)
                def set_node_port_label(self, node_id, port_key, label):
                    pass

                @pyqtSlot(str, str, result=bool)
                def are_port_kinds_compatible(self, _source_kind, _target_kind):
                    return True

                @pyqtSlot(str, str, result=bool)
                def are_data_types_compatible(self, _source_type, _target_type):
                    return True

            class MainWindowBridgeStub(QObject):
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

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                def __init__(self):
                    super().__init__()
                    self.set_selected_node_property_calls = []

                @pyqtSlot(str, "QVariant")
                def set_selected_node_property(self, key, value):
                    self.set_selected_node_property_calls.append((str(key or ""), variant_value(value)))

            scene_bridge = SceneBridgeStub()
            window_bridge = MainWindowBridgeStub()
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene_bridge,
                    "mainWindowBridge": window_bridge,
                },
            )
            def walk_items(item):
                yield item
                for child in item.childItems():
                    yield from walk_items(child)

            node_card = next((item for item in walk_items(canvas) if item.objectName() == "graphNodeCard"), None)
            assert node_card is not None

            canvas.setProperty(
                "pendingConnectionPort",
                {
                    "node_id": "pending-node",
                    "port_key": "exec_out",
                    "direction": "out",
                    "allow_multiple_connections": False,
                    "scene_x": 10.0,
                    "scene_y": 12.0,
                },
            )
            canvas.setProperty(
                "wireDragState",
                {
                    "node_id": "pending-node",
                    "port_key": "exec_out",
                    "source_direction": "out",
                    "start_x": 10.0,
                    "start_y": 12.0,
                    "cursor_x": 20.0,
                    "cursor_y": 30.0,
                    "press_screen_x": 40.0,
                    "press_screen_y": 50.0,
                    "active": True,
                },
            )
            canvas.setProperty(
                "wireDropCandidate",
                {
                    "node_id": "candidate-node",
                    "port_key": "exec_in",
                    "direction": "in",
                    "scene_x": 20.0,
                    "scene_y": 30.0,
                    "valid_drop": True,
                },
            )
            canvas.setProperty("edgeContextVisible", True)
            canvas.setProperty("nodeContextVisible", True)
            canvas.setProperty("selectedEdgeIds", ["edge-1"])
            app.processEvents()

            node_card.surfaceControlInteractionStarted.emit("node_surface_contract_test")
            app.processEvents()

            assert scene_bridge.select_calls == [("node_surface_contract_test", False)]
            assert canvas.property("pendingConnectionPort") is None
            assert canvas.property("wireDragState") is None
            assert canvas.property("wireDropCandidate") is None
            assert not bool(canvas.property("edgeContextVisible"))
            assert not bool(canvas.property("nodeContextVisible"))
            assert variant_list(canvas.property("selectedEdgeIds")) == []

            node_card.inlinePropertyCommitted.emit(
                "node_surface_contract_test",
                "message",
                "updated from graph surface",
            )
            app.processEvents()

            assert scene_bridge.set_node_property_calls == [
                ("node_surface_contract_test", "message", "updated from graph surface")
            ]
            assert window_bridge.set_selected_node_property_calls == []
            assert scene_bridge.select_calls == [
                ("node_surface_contract_test", False),
                ("node_surface_contract_test", False),
            ]

            canvas.deleteLater()
            app.processEvents()
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

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
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

    def test_graph_canvas_supports_surface_control_edits_via_split_canvas_bridges(self) -> None:
        self._run_qml_probe(
            "graph-canvas-split-bridge-surface-control",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

            class CanvasStateBridgeStub(QObject):
                graphics_preferences_changed = pyqtSignal()
                snap_to_grid_changed = pyqtSignal()
                scene_nodes_changed = pyqtSignal()
                scene_edges_changed = pyqtSignal()
                scene_selection_changed = pyqtSignal()
                view_state_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.set_node_property_calls = []
                    self._nodes_model = [node_payload()]
                    self._selected_node_lookup = {}
                    self._width = 640.0
                    self._height = 480.0

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

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                @pyqtProperty(float, constant=True)
                def center_x(self):
                    return 0.0

                @pyqtProperty(float, constant=True)
                def center_y(self):
                    return 0.0

                @pyqtProperty(float, constant=True)
                def zoom_value(self):
                    return 1.0

                @pyqtProperty("QVariantMap", notify=view_state_changed)
                def visible_scene_rect_payload(self):
                    return {
                        "x": -(self._width * 0.5),
                        "y": -(self._height * 0.5),
                        "width": self._width,
                        "height": self._height,
                    }

                @pyqtProperty("QVariantList", notify=scene_nodes_changed)
                def nodes_model(self):
                    return self._nodes_model

                @pyqtProperty("QVariantList", notify=scene_nodes_changed)
                def minimap_nodes_model(self):
                    return self._nodes_model

                @pyqtProperty("QVariantMap", notify=scene_nodes_changed)
                def workspace_scene_bounds_payload(self):
                    return {
                        "x": 0.0,
                        "y": 0.0,
                        "width": 640.0,
                        "height": 480.0,
                    }

                @pyqtProperty("QVariantList", notify=scene_edges_changed)
                def edges_model(self):
                    return []

                @pyqtProperty("QVariantMap", notify=scene_selection_changed)
                def selected_node_lookup(self):
                    return self._selected_node_lookup

                @pyqtSlot(str, str, result=bool)
                def are_port_kinds_compatible(self, _source_kind, _target_kind):
                    return True

                @pyqtSlot(str, str, result=bool)
                def are_data_types_compatible(self, _source_type, _target_type):
                    return True

            class CanvasCommandBridgeStub(QObject):
                def __init__(self, state_bridge):
                    super().__init__()
                    self._state_bridge = state_bridge

                @pyqtSlot(float, float)
                def set_viewport_size(self, width, height):
                    self._state_bridge._width = float(width)
                    self._state_bridge._height = float(height)
                    self._state_bridge.view_state_changed.emit()

                @pyqtSlot(str)
                @pyqtSlot(str, bool)
                def select_node(self, node_id, additive=False):
                    normalized_node_id = str(node_id or "")
                    self._state_bridge.select_calls.append((normalized_node_id, bool(additive)))
                    self._state_bridge._selected_node_lookup = (
                        {normalized_node_id: True} if normalized_node_id else {}
                    )
                    self._state_bridge.scene_selection_changed.emit()

                @pyqtSlot(str, str, "QVariant")
                def set_node_property(self, node_id, key, value):
                    self._state_bridge.set_node_property_calls.append(
                        (str(node_id or ""), str(key or ""), variant_value(value))
                    )

                @pyqtSlot(str, str, str)
                def set_node_port_label(self, node_id, port_key, label):
                    pass

            canvas_state_bridge = CanvasStateBridgeStub()
            canvas_command_bridge = CanvasCommandBridgeStub(canvas_state_bridge)
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )

            def walk_items(item):
                yield item
                for child in item.childItems():
                    yield from walk_items(child)

            node_card = next((item for item in walk_items(canvas) if item.objectName() == "graphNodeCard"), None)
            assert node_card is not None

            node_card.surfaceControlInteractionStarted.emit("node_surface_contract_test")
            app.processEvents()
            node_card.inlinePropertyCommitted.emit(
                "node_surface_contract_test",
                "message",
                "updated through split bridges",
            )
            app.processEvents()

            assert canvas_state_bridge.select_calls == [
                ("node_surface_contract_test", False),
                ("node_surface_contract_test", False),
            ]
            assert canvas_state_bridge.set_node_property_calls == [
                ("node_surface_contract_test", "message", "updated through split bridges")
            ]

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_media_whole_surface_lock_remains_independent_from_local_interactive_rects(self) -> None:
        self._run_qml_probe(
            "media-whole-surface-lock",
            """
            import tempfile
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-contract.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": str(image_path),
                    "caption": "",
                    "fit_mode": "contain",
                }
                host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                drag_area = host.findChild(QObject, "graphNodeDragArea")
                assert surface is not None
                assert loader is not None
                assert drag_area is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break
                assert str(surface.property("previewState")) == "ready"

                window = attach_host_to_window(host)
                hover_host_local_point(window, host, 80.0, 44.0)

                assert len(variant_list(loader.property("embeddedInteractiveRects"))) == 1
                assert not bool(loader.property("blocksHostInteraction"))
                assert bool(drag_area.property("enabled"))

                surface.setProperty("cropModeActive", True)
                app.processEvents()

                assert len(variant_list(loader.property("embeddedInteractiveRects"))) == 10
                assert bool(loader.property("blocksHostInteraction"))
                assert not bool(drag_area.property("enabled"))

                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_graph_scene_bridge_exposes_set_node_property_as_qml_slot(self) -> None:
        from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

        bridge = GraphSceneBridge()
        meta_object = bridge.metaObject()
        method_signatures = [
            bytes(meta_object.method(index).methodSignature()).decode("utf-8")
            for index in range(meta_object.methodOffset(), meta_object.methodCount())
        ]
        self.assertIn("set_node_property(QString,QString,QVariant)", method_signatures)

    def test_shell_window_browse_node_property_path_uses_explicit_node_id(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        window = ShellWindow()
        try:
            image_node_id = window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
            logger_node_id = window.scene.add_node_from_type("core.logger", x=360.0, y=80.0)
            self.assertTrue(image_node_id)
            self.assertTrue(logger_node_id)
            app.processEvents()

            picked_path = str(_REPO_ROOT / "tests" / "fixtures" / "graph-surface-picked-path.png")
            with patch(
                "ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName",
                return_value=(picked_path, ""),
            ) as dialog_mock:
                self.assertEqual(window.browse_selected_node_property_path("source_path", ""), "")
                self.assertEqual(
                    window.browse_node_property_path(image_node_id, "source_path", ""),
                    picked_path,
                )
                self.assertEqual(dialog_mock.call_count, 1)

            self.assertEqual(window.browse_node_property_path(logger_node_id, "message", ""), "")
        finally:
            window.close()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
