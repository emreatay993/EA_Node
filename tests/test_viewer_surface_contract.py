from __future__ import annotations

import unittest
from pathlib import Path

from ea_node_editor.graph.model import GraphModel, NodeInstance
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeRenderQualitySpec, NodeResult, NodeTypeSpec, PortSpec
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from ea_node_editor.ui_qml.graph_surface_metrics import (
    node_surface_metrics,
    viewer_surface_contract_payload,
)
from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    run_qml_probe,
)


class _ViewerSurfacePlugin:
    def __init__(self, spec: NodeTypeSpec) -> None:
        self._spec = spec

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, _ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult()


def _viewer_surface_spec() -> NodeTypeSpec:
    return NodeTypeSpec(
        type_id="tests.viewer_surface_contract",
        display_name="Viewer Contract",
        category_path=("Tests",),
        icon="",
        ports=(
            PortSpec("fields", "in", "data", "dpf_field"),
            PortSpec("session", "out", "data", "dpf_view_session"),
        ),
        properties=(),
        surface_family="viewer",
        render_quality=NodeRenderQualitySpec(
            weight_class="heavy",
            max_performance_strategy="proxy_surface",
            supported_quality_tiers=("full", "proxy"),
        ),
    )


class ViewerSurfaceContractTests(unittest.TestCase):
    def test_graph_viewer_surface_facade_stays_within_packet_budget(self) -> None:
        viewer_dir = Path(__file__).resolve().parents[1] / "ea_node_editor" / "ui_qml" / "components" / "graph" / "viewer"
        facade_path = viewer_dir / "GraphViewerSurface.qml"
        body_path = viewer_dir / "GraphViewerSurfaceBody.qml"
        legacy_content_path = viewer_dir / "GraphViewerSurfaceContent.qml"
        facade_text = facade_path.read_text(encoding="utf-8")

        self.assertFalse(legacy_content_path.exists())
        self.assertTrue(body_path.exists())
        self.assertIn("GraphViewerSurfaceBody.qml", facade_text)
        self.assertIn("dispatchSurfaceAction", facade_text)
        self.assertIn("surfaceActions", facade_text)
        self.assertLessEqual(len(facade_text.splitlines()), 600)


    def test_graph_surface_metrics_facade_stays_within_packet_budget_and_helper_split(self) -> None:
        ui_qml_dir = Path(__file__).resolve().parents[1] / "ea_node_editor" / "ui_qml"
        graph_geometry_dir = ui_qml_dir / "graph_geometry"
        facade_path = ui_qml_dir / "graph_surface_metrics.py"
        facade_text = facade_path.read_text(encoding="utf-8")
        helper_paths = {
            "anchors.py": graph_geometry_dir / "anchors.py",
            "flowchart_metrics.py": graph_geometry_dir / "flowchart_metrics.py",
            "panel_metrics.py": graph_geometry_dir / "panel_metrics.py",
            "standard_metrics.py": graph_geometry_dir / "standard_metrics.py",
            "surface_contract.py": graph_geometry_dir / "surface_contract.py",
            "viewer_metrics.py": graph_geometry_dir / "viewer_metrics.py",
        }

        for snippet in (
            "graph_geometry.anchors",
            "graph_geometry.flowchart_metrics",
            "graph_geometry.panel_metrics",
            "graph_geometry.standard_metrics",
            "graph_geometry.surface_contract",
            "graph_geometry.viewer_metrics",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, facade_text)

        self.assertLessEqual(len(facade_text.splitlines()), 350)

        for helper_name, helper_path in helper_paths.items():
            with self.subTest(helper=helper_name):
                self.assertTrue(helper_path.exists(), msg=f"missing helper {helper_name}")

    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl, pyqtProperty
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.ui.icon_registry import (
                UI_ICON_PROVIDER_ID,
                UiIconImageProvider,
                UiIconRegistryBridge,
            )
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
            engine.addImageProvider(UI_ICON_PROVIDER_ID, UiIconImageProvider())
            engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())
            engine.rootContext().setContextProperty("uiIcons", UiIconRegistryBridge())
            engine.rootContext().setContextProperty("themeBridge", ThemeBridgeStub())
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridgeStub())

            repo_root = Path.cwd()
            graph_node_host_qml_path = repo_root / "ea_node_editor" / "ui_qml" / "components" / "graph" / "GraphNodeHost.qml"

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

            def viewer_payload():
                return {
                    "node_id": "node_viewer_surface_contract",
                    "type_id": "tests.viewer_surface_contract",
                    "title": "Viewer Contract",
                    "x": 120.0,
                    "y": 90.0,
                    "width": 296.0,
                    "height": 236.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "active",
                    "surface_family": "viewer",
                    "surface_variant": "",
                    "render_quality": {
                        "weight_class": "heavy",
                        "max_performance_strategy": "proxy_surface",
                        "supported_quality_tiers": ["full", "proxy"],
                    },
                    "surface_metrics": {
                        "default_width": 296.0,
                        "default_height": 236.0,
                        "min_width": 220.0,
                        "min_height": 208.0,
                        "collapsed_width": 130.0,
                        "collapsed_height": 36.0,
                        "header_height": 24.0,
                        "header_top_margin": 4.0,
                        "body_top": 30.0,
                        "body_height": 176.0,
                        "port_top": 206.0,
                        "port_height": 18.0,
                        "port_center_offset": 6.0,
                        "port_side_margin": 8.0,
                        "port_dot_radius": 3.5,
                        "resize_handle_size": 16.0,
                        "title_top": 4.0,
                        "title_height": 24.0,
                        "title_left_margin": 10.0,
                        "title_right_margin": 42.0,
                        "title_centered": False,
                        "body_left_margin": 14.0,
                        "body_right_margin": 14.0,
                        "body_bottom_margin": 12.0,
                        "show_header_background": True,
                        "show_accent_bar": True,
                        "use_host_chrome": True,
                        "standard_title_full_width": 0.0,
                        "standard_left_label_width": 0.0,
                        "standard_right_label_width": 0.0,
                        "standard_port_gutter": 21.5,
                        "standard_center_gap": 24.0,
                        "standard_port_label_min_width": 0.0,
                    },
                    "viewer_surface": {
                        "body_rect": {"x": 14.0, "y": 30.0, "width": 312.0, "height": 176.0},
                        "proxy_rect": {"x": 14.0, "y": 30.0, "width": 312.0, "height": 176.0},
                        "live_rect": {"x": 14.0, "y": 30.0, "width": 312.0, "height": 176.0},
                        "overlay_target": "body",
                        "proxy_surface_supported": True,
                        "live_surface_supported": True,
                    },
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [
                        {
                            "key": "fields",
                            "label": "Fields",
                            "direction": "in",
                            "kind": "data",
                            "data_type": "dpf_field",
                            "connected": False,
                        },
                        {
                            "key": "session",
                            "label": "Session",
                            "direction": "out",
                            "kind": "data",
                            "data_type": "dpf_view_session",
                            "connected": False,
                        },
                    ],
                    "inline_properties": [],
                }
            """,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

    def test_registry_accepts_viewer_surface_family(self) -> None:
        registry = NodeRegistry()
        spec = _viewer_surface_spec()

        registry.register(lambda: _ViewerSurfacePlugin(spec))

        self.assertEqual(registry.get_spec(spec.type_id).surface_family, "viewer")

    def test_viewer_surface_metrics_publish_reserved_body_contract(self) -> None:
        spec = _viewer_surface_spec()
        node = NodeInstance(
            node_id="node_viewer_surface_contract",
            type_id=spec.type_id,
            title="Viewer Contract",
            x=24.0,
            y=18.0,
        )

        metrics = node_surface_metrics(node, spec, {node.node_id: node})
        contract = viewer_surface_contract_payload(
            width=metrics.default_width,
            height=metrics.default_height,
            surface_metrics=metrics,
        )

        self.assertEqual(metrics.default_width, 340.0)
        self.assertEqual(metrics.default_height, 236.0)
        self.assertEqual(metrics.min_width, 320.0)
        self.assertEqual(metrics.min_height, 208.0)
        self.assertEqual(metrics.body_top, 30.0)
        self.assertEqual(metrics.body_height, 176.0)
        self.assertEqual(metrics.port_top, 206.0)
        self.assertEqual(metrics.title_right_margin, 42.0)
        self.assertTrue(metrics.show_header_background)
        self.assertTrue(metrics.show_accent_bar)
        self.assertTrue(metrics.use_host_chrome)
        self.assertEqual(
            contract,
            {
                "body_rect": {"x": 14.0, "y": 30.0, "width": 312.0, "height": 176.0},
                "proxy_rect": {"x": 14.0, "y": 30.0, "width": 312.0, "height": 176.0},
                "live_rect": {"x": 14.0, "y": 30.0, "width": 312.0, "height": 176.0},
                "overlay_target": "body",
                "proxy_surface_supported": True,
                "live_surface_supported": True,
            },
        )

    def test_surface_metrics_payload_publishes_floating_toolbar_block(self) -> None:
        spec = _viewer_surface_spec()
        node = NodeInstance(
            node_id="node_viewer_surface_contract",
            type_id=spec.type_id,
            title="Viewer Contract",
            x=24.0,
            y=18.0,
        )

        metrics = node_surface_metrics(node, spec, {node.node_id: node})
        payload = metrics.to_payload()

        self.assertIn("floating_toolbar", payload)
        toolbar = payload["floating_toolbar"]
        self.assertIsInstance(toolbar, dict)
        for key in (
            "toolbar_height",
            "button_size",
            "button_gap",
            "internal_padding",
            "gap_from_node",
            "safety_margin",
        ):
            with self.subTest(key=key):
                self.assertIn(key, toolbar)
                self.assertGreater(float(toolbar[key]), 0.0)
        self.assertEqual(float(toolbar["toolbar_height"]), 32.0)
        self.assertEqual(float(toolbar["button_size"]), 24.0)
        self.assertEqual(float(toolbar["button_gap"]), 4.0)
        self.assertEqual(float(toolbar["internal_padding"]), 4.0)
        self.assertEqual(float(toolbar["gap_from_node"]), 6.0)
        self.assertEqual(float(toolbar["safety_margin"]), 8.0)

    def test_graph_scene_payload_builder_publishes_viewer_surface_payload(self) -> None:
        registry = NodeRegistry()
        spec = _viewer_surface_spec()
        registry.register(lambda: _ViewerSurfacePlugin(spec))

        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(
            workspace_id,
            spec.type_id,
            spec.display_name,
            64.0,
            96.0,
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
        self.assertEqual(payload["surface_family"], "viewer")
        self.assertEqual(payload["surface_metrics"]["default_height"], 236.0)
        self.assertEqual(payload["viewer_surface"]["overlay_target"], "body")
        self.assertEqual(payload["viewer_surface"]["live_rect"]["x"], 14.0)
        self.assertEqual(payload["viewer_surface"]["live_rect"]["y"], 30.0)
        self.assertGreater(payload["viewer_surface"]["live_rect"]["width"], 0.0)
        self.assertGreater(payload["viewer_surface"]["live_rect"]["height"], 0.0)
        self.assertEqual(
            payload["render_quality"],
            {
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            },
        )

    def test_graph_node_host_routes_viewer_surface_family_through_loader(self) -> None:
        self._run_qml_probe(
            "viewer-surface-loader-contract",
            """
            from PyQt6.QtCore import QPointF

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": viewer_payload(),
                    "snapshotReuseActive": True,
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            viewport = host.findChild(QObject, "graphNodeViewerViewport")
            assert loader is not None
            assert surface is not None
            assert viewport is not None

            assert host.property("surfaceFamily") == "viewer"
            assert loader.property("loadedSurfaceKey") == "viewer"
            assert host.property("resolvedQualityTier") == "proxy"
            assert bool(surface.property("proxySurfaceActive"))
            assert not bool(surface.property("liveSurfaceActive"))

            contract = variant_value(loader.property("viewerSurfaceContract"))
            assert contract["overlay_target"] == "body"
            assert bool(contract["proxy_surface_supported"])
            assert bool(contract["live_surface_supported"])

            body_rect = loader.property("viewerBodyRect")
            live_rect = loader.property("viewerLiveSurfaceRect")
            assert rect_field(body_rect, "x") == 14.0
            assert rect_field(body_rect, "y") == 30.0
            assert rect_field(body_rect, "width") == 312.0
            assert rect_field(body_rect, "height") == 176.0
            top_left = viewport.mapToItem(surface, QPointF(0.0, 0.0))
            bottom_right = viewport.mapToItem(
                surface,
                QPointF(float(viewport.property("width")), float(viewport.property("height"))),
            )
            assert abs(rect_field(live_rect, "x") - float(top_left.x())) < 0.1
            assert abs(rect_field(live_rect, "y") - float(top_left.y())) < 0.1
            assert abs(rect_field(live_rect, "width") - (float(bottom_right.x()) - float(top_left.x()))) < 0.1
            assert abs(rect_field(live_rect, "height") - (float(bottom_right.y()) - float(top_left.y()))) < 0.1
            assert rect_field(live_rect, "y") > rect_field(body_rect, "y")
            assert rect_field(live_rect, "height") < rect_field(body_rect, "height")
            """,
        )

    def test_viewer_ports_follow_live_resize_preview(self) -> None:
        self._run_qml_probe(
            "viewer-live-resize-port-preview",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": viewer_payload(),
                    "snapshotReuseActive": True,
                },
            )

            initial_metrics = variant_value(host.property("surfaceMetrics"))
            initial_point = variant_value(host.localPortPoint("in", 0))
            assert abs(float(initial_metrics["body_height"]) - 176.0) < 0.1
            assert abs(float(initial_metrics["port_top"]) - 206.0) < 0.1
            assert abs(float(initial_point["y"]) - 212.0) < 0.1

            host.setProperty("_liveWidth", 296.0)
            host.setProperty("_liveHeight", 320.0)
            host.setProperty("_liveGeometryActive", True)
            app.processEvents()

            live_metrics = variant_value(host.property("surfaceMetrics"))
            live_point = variant_value(host.localPortPoint("in", 0))
            assert abs(float(live_metrics["body_height"]) - 260.0) < 0.1
            assert abs(float(live_metrics["port_top"]) - 290.0) < 0.1
            assert abs(float(live_point["y"]) - 296.0) < 0.1
            assert float(live_point["y"]) > float(initial_point["y"])
            """,
        )

    def test_viewer_ports_stay_within_shell_when_height_is_reduced_above_minimum(self) -> None:
        self._run_qml_probe(
            "viewer-mid-height-port-fit",
            """
            payload = viewer_payload()
            payload["height"] = 254.0
            payload["surface_metrics"]["default_height"] = 272.0
            payload["surface_metrics"]["min_height"] = 244.0
            payload["surface_metrics"]["body_height"] = 176.0
            payload["surface_metrics"]["port_top"] = 206.0
            payload["ports"] = [
                {"port_id": "field", "label": "field", "direction": "in", "kind": "data", "data_type": "dpf_field"},
                {"port_id": "model", "label": "model", "direction": "in", "kind": "data", "data_type": "dpf_model"},
                {"port_id": "mesh", "label": "mesh", "direction": "in", "kind": "data", "data_type": "dpf_mesh"},
                {"port_id": "session", "label": "session", "direction": "out", "kind": "data", "data_type": "dpf_view_session"},
            ]

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "snapshotReuseActive": True,
                },
            )

            reduced_metrics = variant_value(host.property("surfaceMetrics"))
            reduced_point = variant_value(host.localPortPoint("in", 2))
            assert abs(float(reduced_metrics["body_height"]) - 158.0) < 0.1
            assert abs(float(reduced_metrics["port_top"]) - 188.0) < 0.1
            assert (
                float(reduced_metrics["port_top"])
                + 3.0 * float(reduced_metrics["port_height"])
                + float(reduced_metrics["body_bottom_margin"])
            ) <= 254.1
            assert float(reduced_point["y"]) <= 254.0
            """,
        )

    def test_viewer_host_clamps_short_payload_height_to_live_surface_minimum(self) -> None:
        self._run_qml_probe(
            "viewer-short-payload-height-clamp",
            """
            payload = viewer_payload()
            payload["height"] = 236.0
            payload["surface_metrics"]["default_height"] = 290.0
            payload["surface_metrics"]["min_height"] = 262.0
            payload["surface_metrics"]["body_height"] = 176.0
            payload["surface_metrics"]["port_top"] = 206.0
            payload["ports"] = [
                {"key": "exec_in", "label": "exec_in", "direction": "in", "kind": "exec", "data_type": "exec", "exposed": True},
                {"key": "exec_out", "label": "exec_out", "direction": "out", "kind": "exec", "data_type": "exec", "exposed": True},
                {"key": "field", "label": "field", "direction": "in", "kind": "data", "data_type": "dpf_field", "exposed": True},
                {"key": "model", "label": "model", "direction": "in", "kind": "data", "data_type": "dpf_model", "exposed": True},
                {"key": "mesh", "label": "mesh", "direction": "in", "kind": "data", "data_type": "dpf_mesh", "exposed": True},
                {"key": "session", "label": "session", "direction": "out", "kind": "data", "data_type": "dpf_view_session", "exposed": True},
            ]

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "snapshotReuseActive": True,
                },
            )

            host_height = float(host.property("height"))
            clamped_metrics = variant_value(host.property("surfaceMetrics"))
            last_input_point = variant_value(host.localPortPoint("in", 3))
            last_output_point = variant_value(host.localPortPoint("out", 1))

            assert abs(host_height - 262.0) < 0.1
            assert abs(float(clamped_metrics["min_height"]) - 262.0) < 0.1
            assert float(last_input_point["y"]) <= host_height
            assert float(last_output_point["y"]) <= host_height
            """,
        )

    def test_viewer_host_heals_stale_default_height_without_explicit_node_height(self) -> None:
        self._run_qml_probe(
            "viewer-stale-default-height-heal",
            """
            payload = viewer_payload()
            del payload["height"]
            payload["surface_metrics"]["default_height"] = 290.0
            payload["surface_metrics"]["min_height"] = 262.0
            payload["surface_metrics"]["body_height"] = 176.0
            payload["surface_metrics"]["port_top"] = 206.0
            payload["ports"] = [
                {"key": "exec_in", "label": "exec_in", "direction": "in", "kind": "exec", "data_type": "exec", "exposed": True},
                {"key": "exec_out", "label": "exec_out", "direction": "out", "kind": "exec", "data_type": "exec", "exposed": True},
                {"key": "field", "label": "field", "direction": "in", "kind": "data", "data_type": "dpf_field", "exposed": True},
                {"key": "model", "label": "model", "direction": "in", "kind": "data", "data_type": "dpf_model", "exposed": True},
                {"key": "mesh", "label": "mesh", "direction": "in", "kind": "data", "data_type": "dpf_mesh", "exposed": True},
                {"key": "session", "label": "session", "direction": "out", "kind": "data", "data_type": "dpf_view_session", "exposed": True},
            ]

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "snapshotReuseActive": True,
                    "graphLabelPixelSize": 16,
                },
            )

            host_height = float(host.property("height"))
            metrics = variant_value(host.property("surfaceMetrics"))
            mesh_row = named_item(host, "graphNodeInputPortRow", "mesh")
            mesh_row_bottom = float(mesh_row.y()) + float(mesh_row.height())

            assert abs(host_height - 314.0) < 0.1
            assert abs(float(metrics["default_height"]) - 314.0) < 0.1
            assert abs(float(metrics["port_height"]) - 24.0) < 0.1
            assert mesh_row_bottom <= host_height - 0.1
            """,
        )

    def test_viewer_host_respects_payload_body_top_when_title_icon_increases_header(self) -> None:
        self._run_qml_probe(
            "viewer-body-top-consistency-with-large-header",
            """
            payload = viewer_payload()
            payload["height"] = 320.0
            payload["surface_metrics"]["default_height"] = 320.0
            payload["surface_metrics"]["min_height"] = 292.0
            payload["surface_metrics"]["header_height"] = 54.0
            payload["surface_metrics"]["title_height"] = 54.0
            payload["surface_metrics"]["body_top"] = 60.0
            payload["surface_metrics"]["body_height"] = 176.0
            payload["surface_metrics"]["port_top"] = 236.0
            payload["surface_metrics"]["port_height"] = 24.0
            payload["ports"] = [
                {"key": "exec_in", "label": "exec_in", "direction": "in", "kind": "exec", "data_type": "exec", "exposed": True},
                {"key": "field", "label": "field", "direction": "in", "kind": "data", "data_type": "dpf_field", "exposed": True},
                {"key": "model", "label": "model", "direction": "in", "kind": "data", "data_type": "dpf_model", "exposed": True},
            ]

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "snapshotReuseActive": True,
                    "graphLabelPixelSize": 16,
                },
            )

            host_height = float(host.property("height"))
            metrics = variant_value(host.property("surfaceMetrics"))
            model_row = named_item(host, "graphNodeInputPortRow", "model")
            model_row_bottom = float(model_row.y()) + float(model_row.height())
            model_point = variant_value(host.localPortPoint("in", 2))

            assert abs(host_height - 320.0) < 0.1
            assert abs(float(metrics["body_height"]) - 176.0) < 0.1
            assert abs(float(metrics["port_top"]) - 236.0) < 0.1
            assert abs(float(model_point["y"]) - 290.0) < 0.1
            assert model_row_bottom <= host_height - 0.1
            """,
        )

    def test_viewer_port_rows_stay_inside_shell_for_large_graph_labels(self) -> None:
        self._run_qml_probe(
            "viewer-large-graph-label-port-fit",
            """
            payload = viewer_payload()
            payload["height"] = 236.0
            payload["surface_metrics"]["default_height"] = 290.0
            payload["surface_metrics"]["min_height"] = 262.0
            payload["surface_metrics"]["body_height"] = 176.0
            payload["surface_metrics"]["port_top"] = 206.0
            payload["ports"] = [
                {"key": "exec_in", "label": "exec_in", "direction": "in", "kind": "exec", "data_type": "exec", "exposed": True},
                {"key": "exec_out", "label": "exec_out", "direction": "out", "kind": "exec", "data_type": "exec", "exposed": True},
                {"key": "field", "label": "field", "direction": "in", "kind": "data", "data_type": "dpf_field", "exposed": True},
                {"key": "model", "label": "model", "direction": "in", "kind": "data", "data_type": "dpf_model", "exposed": True},
                {"key": "mesh", "label": "mesh", "direction": "in", "kind": "data", "data_type": "dpf_mesh", "exposed": True},
                {"key": "session", "label": "session", "direction": "out", "kind": "data", "data_type": "dpf_view_session", "exposed": True},
            ]

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "snapshotReuseActive": True,
                    "graphLabelPixelSize": 16,
                },
            )

            host_height = float(host.property("height"))
            metrics = variant_value(host.property("surfaceMetrics"))
            mesh_row = named_item(host, "graphNodeInputPortRow", "mesh")
            mesh_row_bottom = float(mesh_row.y()) + float(mesh_row.height())

            assert abs(host_height - 286.0) < 0.1
            assert abs(float(metrics["min_height"]) - 286.0) < 0.1
            assert abs(float(metrics["port_height"]) - 24.0) < 0.1
            assert mesh_row_bottom <= host_height - 0.1
            """,
        )

    def test_graph_viewer_surface_contract_includes_bridge_binding_and_control_rects(self) -> None:
        self._run_qml_probe(
            "viewer-surface-bridge-contract",
            """
            from PyQt6.QtCore import pyqtSignal

            class ViewerSessionBridgeStub(QObject):
                sessions_changed = pyqtSignal()

                @pyqtProperty("QVariantList", notify=sessions_changed)
                def sessions_model(self):
                    return [
                        {
                            "workspace_id": "ws_main",
                            "node_id": "node_viewer_surface_contract",
                            "session_id": "session::viewer-contract",
                            "phase": "closed",
                            "request_id": "req::open",
                            "last_command": "open",
                            "last_error": "",
                            "playback_state": "playing",
                            "step_index": 99,
                            "live_policy": "keep_live",
                            "keep_live": True,
                            "cache_state": "live_ready",
                            "backend_id": "backend.legacy",
                            "transport_revision": 99,
                            "live_open_status": "blocked",
                            "live_open_blocker": {"code": "legacy_blocked"},
                            "invalidated_reason": "legacy_invalidated",
                            "close_reason": "legacy_close",
                            "data_refs": {"fields": {"kind": "handle_ref", "handle_id": "handle::fields"}},
                            "transport": {
                                "kind": "bundle",
                                "backend_id": "backend.legacy",
                                "bundle_path": "C:/temp/viewer_bundle",
                            },
                            "summary": {
                                "result_name": "Legacy Displacement",
                                "set_label": "Legacy Set",
                                "cache_state": "live_ready",
                                "backend_id": "backend.legacy",
                                "transport_revision": 99,
                                "live_open_status": "blocked",
                            },
                            "options": {
                                "live_mode": "full",
                                "playback_state": "playing",
                                "step_index": 99,
                                "live_policy": "keep_live",
                                "keep_live": True,
                                "backend_id": "backend.legacy",
                                "transport_revision": 99,
                                "live_open_status": "blocked",
                            },
                            "session_model": {
                                "workspace_id": "ws_main",
                                "node_id": "node_viewer_surface_contract",
                                "session_id": "session::viewer-contract",
                                "phase": "open",
                                "request_id": "req::open",
                                "last_command": "open",
                                "last_error": "",
                                "playback_state": "paused",
                                "step_index": 2,
                                "playback": {"state": "paused", "step_index": 2},
                                "live_policy": "focus_only",
                                "keep_live": False,
                                "cache_state": "proxy_ready",
                                "backend_id": "backend.viewer",
                                "transport_revision": 7,
                                "live_mode": "proxy",
                                "live_open_status": "ready",
                                "live_open_blocker": {},
                                "invalidated_reason": "",
                                "close_reason": "",
                                "data_refs": {"fields": {"kind": "handle_ref", "handle_id": "handle::fields"}},
                                "transport": {
                                    "kind": "bundle",
                                    "backend_id": "backend.viewer",
                                    "bundle_path": "C:/temp/viewer_bundle",
                                },
                                "summary": {
                                    "result_name": "Displacement",
                                    "set_label": "Set 2",
                                    "cache_state": "proxy_ready",
                                    "backend_id": "backend.viewer",
                                    "transport_revision": 7,
                                    "live_open_status": "ready",
                                },
                                "options": {
                                    "live_mode": "proxy",
                                    "playback_state": "paused",
                                    "step_index": 2,
                                    "live_policy": "focus_only",
                                    "keep_live": False,
                                    "backend_id": "backend.viewer",
                                    "transport_revision": 7,
                                    "live_open_status": "ready",
                                },
                            },
                        }
                    ]

                @pyqtProperty(str, constant=True)
                def last_error(self):
                    return ""

            bridge = ViewerSessionBridgeStub()
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)
            host = create_component(graph_node_host_qml_path, {"nodeData": viewer_payload()})
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            assert surface is not None

            interactive_rects = variant_list(surface.property("viewerInteractiveRects"))
            assert interactive_rects == [], interactive_rects

            actions = variant_list(surface.property("surfaceActions"))
            action_ids = [str(action["id"]) for action in actions]
            assert action_ids == ["openSession", "playPause", "step", "keepLive", "fullscreen"], action_ids
            """,
        )

    def test_graph_viewer_surface_fullscreen_action_routes_bridge(self) -> None:
        self._run_qml_probe(
            "viewer-content-fullscreen-action",
            """
            from PyQt6.QtCore import QMetaObject, Q_ARG, pyqtSlot

            class ContentFullscreenBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.toggle_calls = []

                @pyqtSlot(str, result=bool)
                def request_toggle_for_node(self, node_id):
                    self.toggle_calls.append(str(node_id or ""))
                    return True

            bridge = ContentFullscreenBridgeStub()
            engine.rootContext().setContextProperty("contentFullscreenBridge", bridge)

            host = create_component(graph_node_host_qml_path, {"nodeData": viewer_payload()})
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            assert surface is not None
            assert host.findChild(QObject, "graphNodeViewerMoreButton") is None

            actions = variant_list(surface.property("surfaceActions"))
            fullscreen_action = next(action for action in actions if action["id"] == "fullscreen")
            assert bool(fullscreen_action["enabled"])

            QMetaObject.invokeMethod(surface, "dispatchSurfaceAction", Q_ARG("QVariant", "fullscreen"))
            app.processEvents()
            assert bridge.toggle_calls == ["node_viewer_surface_contract"]
            """,
        )
