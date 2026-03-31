from __future__ import annotations

import unittest
from pathlib import Path

from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    run_qml_probe,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


class PassiveGraphSurfaceHostBoundaryTests(unittest.TestCase):
    def test_graph_node_host_routes_theme_and_layout_derivations_through_split_helpers(self) -> None:
        host_text = (_REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml").read_text(encoding="utf-8")
        theme_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml"
        ).read_text(encoding="utf-8")
        layout_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostLayout.qml"
        ).read_text(encoding="utf-8")
        render_quality_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostRenderQuality.qml"
        ).read_text(encoding="utf-8")
        scene_access_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostSceneAccess.qml"
        ).read_text(encoding="utf-8")
        interaction_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostInteractionState.qml"
        ).read_text(encoding="utf-8")

        self.assertIn("GraphNodeHostTheme {", host_text)
        self.assertIn("GraphNodeHostLayout {", host_text)
        self.assertIn("GraphNodeHostRenderQuality {", host_text)
        self.assertIn("GraphNodeHostSceneAccess {", host_text)
        self.assertIn("GraphNodeHostInteractionState {", host_text)
        self.assertIn("readonly property color surfaceColor: themeState.surfaceColor", host_text)
        self.assertIn("readonly property bool _useHostChrome: chromeLayout.useHostChrome", host_text)
        self.assertIn("readonly property var renderQuality: renderQualityState.renderQuality", host_text)
        self.assertIn("return sceneAccess.localPortPoint(direction, rowIndex);", host_text)
        self.assertIn("return interactionState.requestInlineTitleEditAt(localX, localY);", host_text)
        self.assertIn("readonly property color surfaceColor:", theme_text)
        self.assertIn("readonly property bool useHostChrome:", layout_text)
        self.assertIn("readonly property string chromeShadowCacheKey:", layout_text)
        self.assertIn('readonly property string resolvedQualityTier:', render_quality_text)
        self.assertIn("function localPortPoint(direction, rowIndex) {", scene_access_text)
        self.assertIn("function pointInEmbeddedInteractiveRect(localX, localY) {", interaction_text)


class PassiveGraphSurfaceHostTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            """
            import importlib.util
            import sys
            import types
            from pathlib import Path

            from PyQt6.QtCore import QEvent, QObject, QMetaObject, Qt, QUrl, pyqtProperty, pyqtSlot
            from PyQt6.QtGui import QKeyEvent
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtQuick import QQuickItem
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.ui.media_preview_provider import (
                LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
                LocalMediaPreviewImageProvider,
            )

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())

            repo_root = Path.cwd()
            components_dir = repo_root / "ea_node_editor" / "ui_qml" / "components"
            graph_canvas_qml_path = components_dir / "GraphCanvas.qml"
            graph_node_host_qml_path = components_dir / "graph" / "GraphNodeHost.qml"
            node_card_qml_path = components_dir / "graph" / "NodeCard.qml"

            def ensure_namespace(package_name, package_dir):
                if package_name in sys.modules:
                    return
                package = types.ModuleType(package_name)
                package.__path__ = [str(repo_root / package_dir)]
                sys.modules[package_name] = package

            def load_module(module_name, relative_path):
                if module_name in sys.modules:
                    return sys.modules[module_name]
                module_path = repo_root / relative_path
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                assert spec is not None and spec.loader is not None
                sys.modules[module_name] = module
                if module_name == "ea_node_editor.graph.model":
                    def _lazy_symbol(name):
                        def _wrapper(*args, **kwargs):
                            actual = getattr(sys.modules[module_name], name)
                            if actual is _wrapper:
                                raise RuntimeError(f"{module_name}.{name} is not initialized yet")
                            return actual(*args, **kwargs)
                        return _wrapper

                    class _NodeInstancePlaceholder:
                        pass

                    class _EdgeInstancePlaceholder:
                        pass

                    class _ViewStatePlaceholder:
                        pass

                    class _WorkspaceDataPlaceholder:
                        pass

                    class _ProjectDataPlaceholder:
                        pass

                    class _GraphModelPlaceholder:
                        pass

                    module.NodeInstance = _NodeInstancePlaceholder
                    module.EdgeInstance = _EdgeInstancePlaceholder
                    module.ViewState = _ViewStatePlaceholder
                    module.WorkspaceData = _WorkspaceDataPlaceholder
                    module.ProjectData = _ProjectDataPlaceholder
                    module.GraphModel = _GraphModelPlaceholder
                    module.node_instance_from_mapping = _lazy_symbol("node_instance_from_mapping")
                    module.node_instance_to_mapping = _lazy_symbol("node_instance_to_mapping")
                    module.edge_instance_from_mapping = _lazy_symbol("edge_instance_from_mapping")
                    module.edge_instance_to_mapping = _lazy_symbol("edge_instance_to_mapping")
                spec.loader.exec_module(module)
                return module

            ensure_namespace("ea_node_editor.graph", Path("ea_node_editor/graph"))
            ensure_namespace("ea_node_editor.ui_qml", Path("ea_node_editor/ui_qml"))

            GraphModel = load_module(
                "ea_node_editor.graph.model",
                Path("ea_node_editor/graph/model.py"),
            ).GraphModel
            GraphSceneBridge = load_module(
                "ea_node_editor.ui_qml.graph_scene_bridge",
                Path("ea_node_editor/ui_qml/graph_scene_bridge.py"),
            ).GraphSceneBridge
            GraphCanvasStateBridge = load_module(
                "ea_node_editor.ui_qml.graph_canvas_state_bridge",
                Path("ea_node_editor/ui_qml/graph_canvas_state_bridge.py"),
            ).GraphCanvasStateBridge
            GraphCanvasCommandBridge = load_module(
                "ea_node_editor.ui_qml.graph_canvas_command_bridge",
                Path("ea_node_editor/ui_qml/graph_canvas_command_bridge.py"),
            ).GraphCanvasCommandBridge
            ViewportBridge = load_module(
                "ea_node_editor.ui_qml.viewport_bridge",
                Path("ea_node_editor/ui_qml/viewport_bridge.py"),
            ).ViewportBridge

            from ea_node_editor.nodes.bootstrap import build_default_registry

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

            engine.rootContext().setContextProperty("themeBridge", ThemeBridgeStub())
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridgeStub())

            class CanvasShellSource:
                def __init__(self, values=None):
                    for key, value in dict(values or {}).items():
                        setattr(self, str(key), value)

            def _graph_canvas_initial_properties(path, initial_properties):
                normalized = dict(initial_properties)
                if path != graph_canvas_qml_path:
                    return normalized, []
                if "canvasStateBridge" in normalized or "canvasCommandBridge" in normalized:
                    refs = [
                        normalized.get("canvasStateBridge"),
                        normalized.get("canvasCommandBridge"),
                    ]
                    return normalized, [ref for ref in refs if ref is not None]

                scene_bridge = normalized.pop("sceneBridge", None)
                view_bridge = normalized.pop("viewBridge", None)
                shell_source = normalized.pop("mainWindowBridge", None)
                if isinstance(shell_source, dict):
                    shell_source = CanvasShellSource(shell_source)

                state_bridge = GraphCanvasStateBridge(
                    shell_window=shell_source,
                    scene_bridge=scene_bridge,
                    view_bridge=view_bridge,
                )
                command_bridge = GraphCanvasCommandBridge(
                    shell_window=shell_source,
                    scene_bridge=scene_bridge,
                    view_bridge=view_bridge,
                )
                normalized["canvasStateBridge"] = state_bridge
                normalized["canvasCommandBridge"] = command_bridge
                refs = [state_bridge, command_bridge]
                if shell_source is not None:
                    refs.append(shell_source)
                return normalized, refs

            def create_component(path, initial_properties):
                initial_properties, persistent_refs = _graph_canvas_initial_properties(path, initial_properties)
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
                if persistent_refs:
                    setattr(obj, "_graph_canvas_refs", persistent_refs)
                app.processEvents()
                return obj

            class PassiveSurfaceCanvasItem(QQuickItem):
                def __init__(self):
                    super().__init__()
                    self.requested_crop_node_id = ""
                    self.last_committed_node_id = ""
                    self.last_committed_properties = None

                @pyqtSlot(str, result=bool)
                def requestNodeSurfaceCropEdit(self, node_id):
                    self.requested_crop_node_id = str(node_id)
                    return True

                @pyqtSlot(str, result=bool)
                def consumePendingNodeSurfaceAction(self, _node_id):
                    return False

                @pyqtSlot(str, "QVariantMap", result=bool)
                def commitNodeSurfaceProperties(self, node_id, properties):
                    self.last_committed_node_id = str(node_id)
                    self.last_committed_properties = dict(properties or {})
                    return True

                @pyqtSlot(int, result=bool)
                def setNodeSurfaceCursorShape(self, _cursor_shape):
                    return True

                @pyqtSlot(result=bool)
                def clearNodeSurfaceCursorShape(self):
                    return True

                @pyqtSlot(str, "QVariant", result="QVariantMap")
                def describeNodeSurfacePdfPreview(self, _source, _page_number):
                    return {}

            def create_surface_canvas_item():
                return PassiveSurfaceCanvasItem()

            def node_payload(surface_family="standard", surface_variant=""):
                return {
                    "node_id": "node_surface_host_test",
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

            def flowchart_payload(
                variant,
                *,
                title="Decision",
                display_name="Decision",
                collapsed=False,
                properties=None,
                visual_style=None,
            ):
                payload = node_payload(surface_family="flowchart", surface_variant=variant)
                payload["runtime_behavior"] = "passive"
                payload["type_id"] = f"passive.flowchart.{variant}"
                payload["title"] = title
                payload["display_name"] = display_name
                payload["collapsed"] = collapsed
                payload["properties"] = {
                    "title": title,
                    "body": "Review the decision criteria and route accordingly.",
                }
                if properties:
                    payload["properties"].update(properties)
                payload["visual_style"] = {}
                if visual_style:
                    payload["visual_style"].update(visual_style)
                payload["width"] = 236.0
                payload["height"] = 128.0
                payload["ports"] = [
                    {
                        "key": "top",
                        "label": "top",
                        "direction": "neutral",
                        "kind": "flow",
                        "data_type": "flow",
                        "exposed": True,
                        "connected": False,
                    },
                    {
                        "key": "right",
                        "label": "right",
                        "direction": "neutral",
                        "kind": "flow",
                        "data_type": "flow",
                        "exposed": True,
                        "connected": False,
                    },
                    {
                        "key": "bottom",
                        "label": "bottom",
                        "direction": "neutral",
                        "kind": "flow",
                        "data_type": "flow",
                        "exposed": True,
                        "connected": False,
                    },
                    {
                        "key": "left",
                        "label": "left",
                        "direction": "neutral",
                        "kind": "flow",
                        "data_type": "flow",
                        "exposed": True,
                        "connected": False,
                    },
                ]
                payload["inline_properties"] = []
                return payload
            """,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

    def test_graph_node_host_loads_standard_surface_for_standard_nodes(self) -> None:
        self._run_qml_probe(
            "standard-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            assert host.objectName() == "graphNodeCard"
            assert host.property("surfaceFamily") == "standard"
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None
            assert loader.property("loadedSurfaceKey") == "standard"
            assert host.findChild(QObject, "graphNodeStandardSurface") is not None
            """,
        )

    def test_graph_node_host_falls_back_to_standard_surface_for_unknown_family(self) -> None:
        self._run_qml_probe(
            "fallback-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": node_payload(surface_family="mystery", surface_variant="sticky_note")},
            )
            assert host.property("surfaceFamily") == "mystery"
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None
            assert loader.property("loadedSurfaceKey") == "standard"
            assert host.findChild(QObject, "graphNodeStandardSurface") is not None
            """,
        )

    def test_graph_node_host_uses_curve_rendering_for_node_text(self) -> None:
        self._run_qml_probe(
            "curve-rendering-host",
            """
            standard_host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            expected_render_type = standard_host.property("nodeTextRenderType")
            title_item = standard_host.findChild(QObject, "graphNodeTitle")
            input_labels = named_child_items(standard_host, "graphNodeInputPortLabel")
            assert title_item is not None
            assert len(input_labels) >= 1
            assert title_item.property("effectiveRenderType") == expected_render_type
            assert input_labels[0].property("effectiveRenderType") == expected_render_type

            annotation_payload = node_payload(surface_family="annotation", surface_variant="sticky_note")
            annotation_payload["runtime_behavior"] = "passive"
            annotation_payload["properties"] = {"body": "Sticky note"}
            annotation_host = create_component(graph_node_host_qml_path, {"nodeData": annotation_payload})
            annotation_text = annotation_host.findChild(QObject, "graphNodeAnnotationBodyText")
            assert annotation_text is not None
            assert annotation_text.property("effectiveRenderType") == annotation_host.property("nodeTextRenderType")

            planning_payload = node_payload(surface_family="planning", surface_variant="task_card")
            planning_payload["runtime_behavior"] = "passive"
            planning_payload["properties"] = {
                "body": "Follow up with render pass",
                "status": "in progress",
                "owner": "Alex",
                "due_date": "Tomorrow",
            }
            planning_host = create_component(graph_node_host_qml_path, {"nodeData": planning_payload})
            planning_text = planning_host.findChild(QObject, "graphNodePlanningBodyText")
            assert planning_text is not None
            assert planning_text.property("effectiveRenderType") == planning_host.property("nodeTextRenderType")

            media_payload = node_payload(surface_family="media", surface_variant="image_panel")
            media_payload["runtime_behavior"] = "passive"
            media_payload["properties"] = {"caption": "Preview caption"}
            media_host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
            caption_text = media_host.findChild(QObject, "graphNodeMediaCaption")
            assert caption_text is not None
            assert caption_text.property("effectiveRenderType") == media_host.property("nodeTextRenderType")
            """,
        )

    def test_expanded_flowchart_body_text_replaces_visible_header_title_and_double_click_enters_inline_edit(self) -> None:
        self._run_qml_probe(
            "flowchart-body-text-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": flowchart_payload("decision")})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                title_item = host.findChild(QObject, "graphNodeTitle")
                title_editor = host.findChild(QObject, "graphNodeTitleEditor")
                body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
                body_editor = host.findChild(QObject, "graphNodeFlowchartBodyEditor")
                body_field = host.findChild(QObject, "graphNodeFlowchartBodyEditorField")
                assert title_item is not None
                assert title_editor is not None
                assert body_text is not None
                assert body_editor is not None
                assert body_field is not None

                events = host_pointer_events(host)
                interactions = []
                host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
                body_point = item_scene_point(body_text)

                assert not bool(title_item.property("visible"))
                assert not bool(title_editor.property("visible"))
                assert str(body_text.property("text") or "") == "Review the decision criteria and route accordingly."
                assert bool(body_text.property("visible"))
                assert not bool(body_editor.property("visible"))

                mouse_click(window, body_point)
                assert events["clicked"] == [("node_surface_host_test", False)]
                assert events["opened"] == []
                assert not bool(body_editor.property("visible"))

                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_double_click(window, body_point)
                settle_events(5)

                assert not bool(title_editor.property("visible"))
                assert not bool(body_text.property("visible"))
                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))
                assert str(body_field.property("text") or "") == "Review the decision criteria and route accordingly."
                assert int(body_field.property("cursorPosition")) == len(str(body_field.property("text") or ""))
                assert len(interactions) >= 1
                assert all(node_id == "node_surface_host_test" for node_id in interactions)
                assert events["opened"] == []
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_expanded_flowchart_body_text_uses_fallback_chain_and_passive_style_hooks(self) -> None:
        self._run_qml_probe(
            "flowchart-body-fallback-style-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": flowchart_payload(
                        "decision",
                        title="Archive",
                        properties={"title": "Archive", "body": "   "},
                        visual_style={
                            "text_color": "#204060",
                            "font_size": 17,
                            "font_weight": "bold",
                        },
                    ),
                },
            )
            title_item = host.findChild(QObject, "graphNodeTitle")
            body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
            assert title_item is not None
            assert body_text is not None
            assert not bool(title_item.property("visible"))
            assert bool(body_text.property("visible"))
            assert str(body_text.property("text") or "") == "Archive"
            body_font = body_text.property("font")
            assert body_font.pixelSize() == 17
            assert body_font.bold()
            assert body_text.property("color").name().lower() == "#204060"
            """,
        )

    def test_expanded_flowchart_body_editor_commits_from_external_click_path(self) -> None:
        self._run_qml_probe(
            "flowchart-body-external-click-commit-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": flowchart_payload("decision")})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
                body_editor = host.findChild(QObject, "graphNodeFlowchartBodyEditor")
                body_field = host.findChild(QObject, "graphNodeFlowchartBodyEditorField")
                assert body_text is not None
                assert body_editor is not None
                assert body_field is not None

                events = host_pointer_events(host)
                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(body_text))
                settle_events(5)
                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))

                body_field.setProperty("text", "Approve request\\nNotify requester")
                app.processEvents()

                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_click(window, host_scene_point(host, 24.0, 6.0))
                settle_events(5)

                assert committed == [("node_surface_host_test", "body", "Approve request\\nNotify requester")]
                assert events["clicked"] == [("node_surface_host_test", False)]
                assert events["opened"] == []
                assert events["contexts"] == []
                assert bool(body_text.property("visible"))
                assert not bool(body_editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_expanded_flowchart_body_editor_cancels_and_closes_on_escape(self) -> None:
        self._run_qml_probe(
            "flowchart-body-escape-cancel-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": flowchart_payload("decision")})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
                body_editor = host.findChild(QObject, "graphNodeFlowchartBodyEditor")
                body_field = host.findChild(QObject, "graphNodeFlowchartBodyEditorField")
                assert body_text is not None
                assert body_editor is not None
                assert body_field is not None

                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(body_text))
                settle_events(5)
                assert bool(body_editor.property("visible"))

                body_field.setProperty("text", "Discard this draft")
                app.processEvents()
                app.sendEvent(
                    body_field,
                    QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                )
                app.sendEvent(
                    body_field,
                    QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                )
                settle_events(5)

                assert committed == []
                assert bool(body_text.property("visible"))
                assert not bool(body_editor.property("visible"))
                assert str(body_field.property("text") or "") == "Review the decision criteria and route accordingly."
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_passive_planning_body_text_double_click_commits_and_cancels_inline_edits(self) -> None:
        self._run_qml_probe(
            "planning-inline-body-edit-host",
            """
            payload = node_payload(surface_family="planning", surface_variant="decision_card")
            payload["runtime_behavior"] = "passive"
            payload["type_id"] = "passive.planning.decision_card"
            payload["properties"] = {
                "body": "Review the decision criteria and route accordingly.",
                "state": "open",
                "status": "open",
                "outcome": "",
            }

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_text = host.findChild(QObject, "graphNodePlanningBodyText")
                body_editor = host.findChild(QObject, "graphNodePlanningBodyEditor")
                body_field = host.findChild(QObject, "graphNodePlanningBodyEditorField")
                assert body_text is not None
                assert body_editor is not None
                assert body_field is not None

                events = host_pointer_events(host)
                interactions = []
                committed = []
                host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                body_point = item_scene_point(body_text)
                mouse_double_click(window, body_point)
                settle_events(5)

                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))
                assert str(body_field.property("text") or "") == "Review the decision criteria and route accordingly."
                assert len(interactions) >= 1
                assert all(node_id == "node_surface_host_test" for node_id in interactions)
                assert events["opened"] == []

                body_field.setProperty("text", "Approve path A\\nNotify the team")
                app.processEvents()
                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_click(window, host_scene_point(host, 24.0, 8.0))
                settle_events(5)

                assert committed == [("node_surface_host_test", "body", "Approve path A\\nNotify the team")]
                assert events["opened"] == []
                assert not bool(body_editor.property("visible"))
                assert bool(body_text.property("visible"))

                committed.clear()
                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_double_click(window, body_point)
                settle_events(5)
                assert bool(body_editor.property("visible"))

                body_field.setProperty("text", "Discard this draft")
                app.processEvents()
                app.sendEvent(
                    body_field,
                    QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                )
                app.sendEvent(
                    body_field,
                    QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                )
                settle_events(5)

                assert committed == []
                assert not bool(body_editor.property("visible"))
                assert bool(body_text.property("visible"))
                assert events["opened"] == []
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_passive_annotation_body_text_double_click_edits_body_and_subtitle_inline(self) -> None:
        self._run_qml_probe(
            "annotation-inline-edit-host",
            """
            def run_annotation_case(
                label,
                payload,
                text_object_name,
                editor_object_name,
                field_object_name,
                key,
                *,
                commit_via_keyboard=False,
            ):
                host = create_component(graph_node_host_qml_path, {"nodeData": payload})
                window = attach_host_to_window(host, width=640, height=480)
                try:
                    text_item = host.findChild(QObject, text_object_name)
                    editor = host.findChild(QObject, editor_object_name)
                    field = host.findChild(QObject, field_object_name)
                    assert text_item is not None, label
                    assert editor is not None, label
                    assert field is not None, label

                    events = host_pointer_events(host)
                    interactions = []
                    committed = []
                    host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
                    host.inlinePropertyCommitted.connect(
                        lambda node_id, committed_key, value: committed.append((node_id, committed_key, variant_value(value)))
                    )

                    text_point = item_scene_point(text_item)
                    mouse_double_click(window, text_point)
                    settle_events(10 if commit_via_keyboard else 5)

                    assert bool(editor.property("visible")), label
                    assert bool(field.property("activeFocus")), label
                    assert len(interactions) >= 1, label
                    assert all(node_id == "node_surface_host_test" for node_id in interactions), label
                    assert events["opened"] == [], label

                    field.setProperty("text", f"Edited {label}")
                    app.processEvents()
                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()

                    if commit_via_keyboard:
                        app.sendEvent(
                            field,
                            QKeyEvent(
                                QEvent.Type.KeyPress,
                                Qt.Key.Key_Enter,
                                Qt.KeyboardModifier.ControlModifier,
                            ),
                        )
                        app.sendEvent(
                            field,
                            QKeyEvent(
                                QEvent.Type.KeyRelease,
                                Qt.Key.Key_Enter,
                                Qt.KeyboardModifier.ControlModifier,
                            ),
                        )
                    else:
                        mouse_click(window, host_scene_point(host, 24.0, 8.0))
                    settle_events(10 if commit_via_keyboard else 5)

                    assert committed == [("node_surface_host_test", key, f"Edited {label}")], label
                    assert not bool(editor.property("visible")), label
                    assert events["opened"] == [], label
                finally:
                    dispose_host_window(host, window)

            sticky_payload = node_payload(surface_family="annotation", surface_variant="sticky_note")
            sticky_payload["runtime_behavior"] = "passive"
            sticky_payload["type_id"] = "passive.annotation.sticky_note"
            sticky_payload["properties"] = {"body": "Sticky note body"}
            run_annotation_case(
                "sticky-note-body",
                sticky_payload,
                "graphNodeAnnotationBodyText",
                "graphNodeAnnotationBodyEditor",
                "graphNodeAnnotationBodyEditorField",
                "body",
            )

            section_payload = node_payload(surface_family="annotation", surface_variant="section_header")
            section_payload["runtime_behavior"] = "passive"
            section_payload["type_id"] = "passive.annotation.section_header"
            section_payload["properties"] = {"subtitle": "Section subtitle"}
            run_annotation_case(
                "section-header-subtitle",
                section_payload,
                "graphNodeAnnotationSubtitleText",
                "graphNodeAnnotationBodyEditor",
                "graphNodeAnnotationSubtitleEditorField",
                "subtitle",
                commit_via_keyboard=True,
            )
            """,
        )

    def test_passive_planning_empty_body_area_double_click_enters_edit_and_blur_closes_without_commit(self) -> None:
        self._run_qml_probe(
            "planning-empty-body-inline-edit-host",
            """
            payload = node_payload(surface_family="planning", surface_variant="decision_card")
            payload["runtime_behavior"] = "passive"
            payload["type_id"] = "passive.planning.decision_card"
            payload["properties"] = {
                "body": "",
                "state": "open",
                "status": "open",
                "outcome": "",
            }

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_editor = host.findChild(QObject, "graphNodePlanningBodyEditor")
                body_field = host.findChild(QObject, "graphNodePlanningBodyEditorField")
                assert body_editor is not None
                assert body_field is not None

                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(body_editor))
                settle_events(5)

                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))
                assert str(body_field.property("text") or "") == ""

                mouse_click(window, host_scene_point(host, 24.0, 8.0))
                settle_events(5)

                assert committed == []
                assert not bool(body_editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_passive_annotation_empty_body_area_double_click_enters_edit_and_blur_closes_without_commit(self) -> None:
        self._run_qml_probe(
            "annotation-empty-body-inline-edit-host",
            """
            payload = node_payload(surface_family="annotation", surface_variant="sticky_note")
            payload["runtime_behavior"] = "passive"
            payload["type_id"] = "passive.annotation.sticky_note"
            payload["properties"] = {"body": ""}

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_editor = host.findChild(QObject, "graphNodeAnnotationBodyEditor")
                body_field = host.findChild(QObject, "graphNodeAnnotationBodyEditorField")
                assert body_editor is not None
                assert body_field is not None

                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(body_editor))
                settle_events(5)

                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))
                assert str(body_field.property("text") or "") == ""

                mouse_click(window, host_scene_point(host, 24.0, 8.0))
                settle_events(5)

                assert committed == []
                assert not bool(body_editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_collapsed_flowchart_keeps_compact_header_title_behavior(self) -> None:
        self._run_qml_probe(
            "flowchart-collapsed-title-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": flowchart_payload("decision", title="Archive", collapsed=True)},
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            title_item = host.findChild(QObject, "graphNodeTitle")
            editor = host.findChild(QObject, "graphNodeTitleEditor")
            body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
            assert loader is not None
            assert title_item is not None
            assert editor is not None
            assert body_text is None
            assert not bool(loader.property("surfaceLoaded"))
            assert bool(title_item.property("visible"))
            assert str(title_item.property("text") or "") == "Archive"
            assert not bool(editor.property("visible"))
            """,
        )

    def test_non_scoped_standard_and_passive_titles_use_shared_header_editor_without_pointer_leaks(self) -> None:
        self._run_qml_probe(
            "shared-header-title-rollout-host",
            """
            def passive_standard_payload():
                payload = node_payload()
                payload["runtime_behavior"] = "passive"
                payload["type_id"] = "passive.standard.note"
                payload["title"] = "Passive Note"
                payload["properties"] = {"title": "Passive Note"}
                payload["visual_style"] = {
                    "fill_color": "#f3f8fd",
                    "border_color": "#6f88a3",
                    "text_color": "#173247",
                    "header_color": "#deebf7",
                }
                return payload

            scenarios = [
                ("standard", node_payload(), "Approved"),
                ("passive", passive_standard_payload(), "Reviewed"),
            ]

            for label, payload, committed_title in scenarios:
                host = create_component(graph_node_host_qml_path, {"nodeData": payload})
                window = attach_host_to_window(host, width=640, height=480)
                try:
                    title_item = host.findChild(QObject, "graphNodeTitle")
                    editor = host.findChild(QObject, "graphNodeTitleEditor")
                    assert title_item is not None, label
                    assert editor is not None, label
                    assert bool(host.property("sharedHeaderTitleEditable")), label

                    events = host_pointer_events(host)
                    interactions = []
                    committed = []
                    host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
                    host.inlinePropertyCommitted.connect(
                        lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                    )

                    title_point = item_scene_point(title_item)
                    body_point = host_scene_point(
                        host,
                        float(host.property("width")) * 0.5,
                        float(host.property("height")) * 0.78,
                    )

                    mouse_click(window, title_point)
                    assert events["clicked"] == [(payload["node_id"], False)], label
                    assert events["opened"] == [], label
                    assert not bool(editor.property("visible")), label

                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()

                    mouse_double_click(window, title_point)
                    settle_events(5)
                    assert bool(editor.property("visible")), label
                    assert str(editor.property("selectedText") or "") == "", label
                    assert int(editor.property("cursorPosition")) == len(str(payload["title"])), label
                    assert interactions == [payload["node_id"]], label
                    assert events["opened"] == [], label

                    editor.setProperty("text", f" {committed_title} ")
                    app.processEvents()
                    app.sendEvent(
                        editor,
                        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
                    )
                    app.sendEvent(
                        editor,
                        QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
                    )
                    settle_events(5)
                    assert committed == [(payload["node_id"], "title", committed_title)], label
                    assert not bool(editor.property("visible")), label

                    committed.clear()
                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()

                    mouse_double_click(window, title_point)
                    settle_events(5)
                    assert bool(editor.property("visible")), label

                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()
                    editor_point = item_scene_point(editor)
                    mouse_click(window, editor_point)
                    mouse_double_click(window, editor_point)
                    mouse_click(window, editor_point, Qt.MouseButton.RightButton)
                    settle_events(5)
                    assert events["clicked"] == [], label
                    assert events["opened"] == [], label
                    assert events["contexts"] == [], label

                    app.sendEvent(
                        editor,
                        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                    )
                    app.sendEvent(
                        editor,
                        QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                    )
                    settle_events(5)
                    assert committed == [], label
                    assert not bool(editor.property("visible")), label

                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()
                    mouse_double_click(window, body_point)
                    settle_events(5)
                    assert events["opened"] == [payload["node_id"]], label
                finally:
                    dispose_host_window(host, window)
            """,
        )

    def test_scope_capable_nodes_publish_open_badge_hit_region_and_keep_title_double_click_for_editing(self) -> None:
        self._run_qml_probe(
            "shared-header-title-rollout-scope-open-badge",
            """
            payload = node_payload()
            payload["can_enter_scope"] = True

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                header = host.findChild(QObject, "graphNodeHeaderLayer")
                title_item = host.findChild(QObject, "graphNodeTitle")
                editor = host.findChild(QObject, "graphNodeTitleEditor")
                open_badge = host.findChild(QObject, "graphNodeOpenBadge")
                assert header is not None
                assert title_item is not None
                assert editor is not None
                assert open_badge is not None
                assert bool(host.property("sharedHeaderTitleEditable"))

                embedded_rects = variant_list(header.property("embeddedInteractiveRects"))
                assert len(embedded_rects) == 1
                badge_rect = embedded_rects[0]
                badge_local_point = open_badge.mapToItem(
                    host,
                    QPointF(float(open_badge.width()) * 0.5, float(open_badge.height()) * 0.5),
                )
                badge_local_x = float(badge_local_point.x())
                badge_local_y = float(badge_local_point.y())
                assert rect_field(badge_rect, "x") <= badge_local_x <= (
                    rect_field(badge_rect, "x") + rect_field(badge_rect, "width")
                )
                assert rect_field(badge_rect, "y") <= badge_local_y <= (
                    rect_field(badge_rect, "y") + rect_field(badge_rect, "height")
                )

                committed = []
                events = host_pointer_events(host)
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )
                mouse_double_click(window, item_scene_point(title_item))
                settle_events(5)

                assert bool(editor.property("visible"))
                assert events["opened"] == []

                editor.setProperty("text", " Scoped Logger ")
                app.processEvents()
                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_click(window, item_scene_point(open_badge))
                settle_events(5)

                assert committed == [("node_surface_host_test", "title", "Scoped Logger")]
                assert events["clicked"] == []
                assert events["opened"] == ["node_surface_host_test"]
                assert events["contexts"] == []
                assert not bool(editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_collapsed_nodes_use_shared_header_editor_for_title_commits(self) -> None:
        self._run_qml_probe(
            "shared-header-title-rollout-collapsed-host",
            """
            payload = node_payload()
            payload["collapsed"] = True

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                title_item = host.findChild(QObject, "graphNodeTitle")
                editor = host.findChild(QObject, "graphNodeTitleEditor")
                assert title_item is not None
                assert editor is not None
                assert bool(host.property("sharedHeaderTitleEditable"))

                committed = []
                events = host_pointer_events(host)
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(title_item))
                settle_events(5)
                assert bool(editor.property("visible"))
                assert events["opened"] == []

                editor.setProperty("text", " Collapsed Logger ")
                app.processEvents()
                app.sendEvent(
                    editor,
                    QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
                )
                app.sendEvent(
                    editor,
                    QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
                )
                settle_events(5)

                assert committed == [("node_surface_host_test", "title", "Collapsed Logger")]
                assert not bool(editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_media_host_proxy_surface_activates_when_ready_image_enters_proxy_quality_tier(self) -> None:
        self._run_qml_probe(
            "media-render-quality-proxy-surface",
            """
            import tempfile

            from PyQt6.QtGui import QColor, QImage

            media_payload = node_payload(surface_family="media", surface_variant="image_panel")
            media_payload["runtime_behavior"] = "passive"
            media_payload["type_id"] = "passive.media.image_panel"
            media_payload["title"] = "Image Panel"
            media_payload["width"] = 296.0
            media_payload["height"] = 236.0
            media_payload["surface_metrics"] = {
                "body_height": 180.0,
            }
            media_payload["ports"] = []
            media_payload["inline_properties"] = []
            media_payload["render_quality"] = {
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            }

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "proxy-image.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))
                media_payload["properties"] = {
                    "source_path": str(image_path),
                    "caption": "Proxy seam",
                    "fit_mode": "contain",
                }

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": media_payload,
                        "snapshotReuseActive": True,
                        "shadowSimplificationActive": True,
                    },
                )
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                proxy_preview = host.findChild(QObject, "graphNodeMediaProxyPreview")
                applied_viewport = host.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                assert loader is not None
                assert surface is not None
                assert proxy_preview is not None
                assert applied_viewport is not None

                for _index in range(50):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break

                render_quality = variant_value(host.property("renderQuality"))
                context = variant_value(host.property("surfaceQualityContext"))

                assert surface.property("previewState") == "ready"
                assert render_quality == {
                    "weight_class": "heavy",
                    "max_performance_strategy": "proxy_surface",
                    "supported_quality_tiers": ["full", "proxy"],
                }
                assert host.property("requestedQualityTier") == "reduced"
                assert host.property("resolvedQualityTier") == "proxy"
                assert bool(host.property("proxySurfaceRequested"))
                assert loader.property("requestedQualityTier") == "reduced"
                assert loader.property("resolvedQualityTier") == "proxy"
                assert bool(loader.property("proxySurfaceRequested"))
                assert bool(loader.property("proxySurfaceActive"))
                assert bool(proxy_preview.property("visible"))
                assert not bool(applied_viewport.property("visible"))
                assert context["resolved_quality_tier"] == "proxy"
                assert bool(context["proxy_surface_requested"])
                assert bool(surface.property("proxySurfaceActive"))
                assert surface.property("host").property("resolvedQualityTier") == "proxy"
                assert loader.property("loadedSurfaceKey") == "media"
            """,
        )

    def test_standard_host_keeps_port_labels_tied_to_port_handles(self) -> None:
        self._run_qml_probe(
            "port-label-geometry-host",
            """
            payload = node_payload()
            payload["width"] = 320.0
            payload["surface_metrics"]["default_width"] = 320.0
            payload["ports"][0]["label"] = "in"
            payload["ports"][1]["label"] = "out"

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            output_dot = named_child_items(host, "graphNodeOutputPortDot")[0]
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]

            gap = float(host.property("_portLabelGap"))
            max_width = float(host.property("_portLabelMaxWidth"))
            output_implicit_width = float(output_label.property("implicitWidth"))
            input_label_left = input_label.mapToItem(host, QPointF(0.0, 0.0)).x()
            output_label_right = output_label.mapToItem(host, QPointF(float(output_label.width()), 0.0)).x()

            assert abs(input_label_left - (input_dot.x() + input_dot.width() + gap)) < 0.5
            assert abs(output_label_right - (output_dot.x() - gap)) < 0.5
            assert output_label.width() < max_width
            assert abs(output_label.width() - output_implicit_width) < 0.5
            """,
        )

    def test_standard_host_replaces_default_exec_port_labels_with_arrows(self) -> None:
        self._run_qml_probe(
            "exec-port-arrow-labels-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]
            input_mouse = named_child_items(host, "graphNodeInputPortMouseArea")[0]
            output_mouse = named_child_items(host, "graphNodeOutputPortMouseArea")[0]

            assert input_label.property("text") == "\u27A1"
            assert output_label.property("text") == "\u27A1"
            assert input_mouse.property("portLabelTooltipText") == "Exec In"
            assert output_mouse.property("portLabelTooltipText") == "Exec Out"
            """,
        )

    def test_standard_host_consumes_metric_backed_label_columns_without_overlap(self) -> None:
        self._run_qml_probe(
            "port-label-width-contract-host",
            """
            payload = node_payload()
            payload["ports"][0]["label"] = "Primary Input Payload"
            payload["ports"][1]["label"] = "Dispatch Result Token"
            payload["width"] = 360.0
            payload["surface_metrics"]["default_width"] = 360.0

            measurement_host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            measurement_input = named_child_items(measurement_host, "graphNodeInputPortLabel")[0]
            measurement_output = named_child_items(measurement_host, "graphNodeOutputPortLabel")[0]
            left_width = float(measurement_input.property("implicitWidth"))
            right_width = float(measurement_output.property("implicitWidth"))
            measurement_host.deleteLater()
            app.processEvents()

            port_gutter = 21.5
            center_gap = 24.0
            min_width = left_width + right_width + (port_gutter * 2.0) + center_gap
            payload["width"] = min_width
            payload["surface_metrics"]["default_width"] = min_width
            payload["surface_metrics"]["min_width"] = min_width
            payload["surface_metrics"]["standard_left_label_width"] = left_width
            payload["surface_metrics"]["standard_right_label_width"] = right_width
            payload["surface_metrics"]["standard_port_gutter"] = port_gutter
            payload["surface_metrics"]["standard_center_gap"] = center_gap
            payload["surface_metrics"]["standard_port_label_min_width"] = min_width

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            output_dot = named_child_items(host, "graphNodeOutputPortDot")[0]
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]

            assert bool(host.property("_usesStandardPortLabelColumns"))
            assert abs(float(input_label.width()) - left_width) < 0.75
            assert abs(float(output_label.width()) - right_width) < 0.75

            gap = float(host.property("_portLabelGap"))
            input_left = input_label.mapToItem(host, QPointF(0.0, 0.0)).x()
            input_right = input_label.mapToItem(host, QPointF(float(input_label.width()), 0.0)).x()
            output_left = output_label.mapToItem(host, QPointF(0.0, 0.0)).x()
            output_right = output_label.mapToItem(host, QPointF(float(output_label.width()), 0.0)).x()

            assert abs(input_left - (input_dot.x() + input_dot.width() + gap)) < 0.5
            assert abs(output_right - (output_dot.x() - gap)) < 0.5
            assert output_left - input_right >= center_gap - 0.5
            """,
        )

    def test_standard_host_uses_extra_width_to_expand_metric_backed_label_columns(self) -> None:
        self._run_qml_probe(
            "port-label-extra-width-host",
            """
            payload = node_payload()
            payload["ports"][0]["label"] = "Primary Input Payload"
            payload["ports"][1]["label"] = "Dispatch Result Token"
            payload["width"] = 360.0
            payload["surface_metrics"]["default_width"] = 360.0

            measurement_host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            measurement_input = named_child_items(measurement_host, "graphNodeInputPortLabel")[0]
            measurement_output = named_child_items(measurement_host, "graphNodeOutputPortLabel")[0]
            left_width = float(measurement_input.property("implicitWidth"))
            right_width = float(measurement_output.property("implicitWidth"))
            measurement_host.deleteLater()
            app.processEvents()

            metric_left_width = max(20.0, left_width - 12.0)
            metric_right_width = max(20.0, right_width - 12.0)
            port_gutter = 21.5
            center_gap = 24.0
            min_width = metric_left_width + metric_right_width + (port_gutter * 2.0) + center_gap
            payload["width"] = min_width + 24.0
            payload["surface_metrics"]["default_width"] = payload["width"]
            payload["surface_metrics"]["min_width"] = min_width
            payload["surface_metrics"]["standard_left_label_width"] = metric_left_width
            payload["surface_metrics"]["standard_right_label_width"] = metric_right_width
            payload["surface_metrics"]["standard_port_gutter"] = port_gutter
            payload["surface_metrics"]["standard_center_gap"] = center_gap
            payload["surface_metrics"]["standard_port_label_min_width"] = min_width

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]

            assert bool(host.property("_usesStandardPortLabelColumns"))
            assert float(input_label.width()) > metric_left_width + 10.0
            assert float(output_label.width()) > metric_right_width + 10.0
            assert abs(float(input_label.width()) - left_width) < 0.75
            assert abs(float(output_label.width()) - right_width) < 0.75
            """,
        )

    def test_standard_host_uses_tooltip_only_port_labels_when_preference_disabled(self) -> None:
        self._run_qml_probe(
            "tooltip-only-port-labels-host",
            """
            payload = node_payload()
            payload["ports"][0]["label"] = "Primary Input Payload"
            payload["ports"][1]["label"] = "Dispatch Result Token"

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "showPortLabelsPreference": False,
                },
            )
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]
            input_mouse = named_child_items(host, "graphNodeInputPortMouseArea")[0]
            output_mouse = named_child_items(host, "graphNodeOutputPortMouseArea")[0]

            assert bool(host.property("_tooltipOnlyPortLabelsActive"))
            assert not bool(host.property("_portLabelsVisible"))
            assert not bool(input_label.property("visible"))
            assert not bool(output_label.property("visible"))
            assert bool(input_mouse.property("tooltipOnlyPortLabelActive"))
            assert bool(output_mouse.property("tooltipOnlyPortLabelActive"))
            assert input_mouse.property("portLabelTooltipText") == "Primary Input Payload"
            assert output_mouse.property("portLabelTooltipText") == "Dispatch Result Token"

            window = attach_host_to_window(host)
            try:
                QTest.mouseMove(window, item_scene_point(input_mouse))
                settle_events(5)
                assert bool(input_mouse.property("containsMouse"))
                assert bool(input_mouse.property("tooltipVisible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_standard_host_marks_inactive_input_ports_with_muted_label_and_reason_tooltip(self) -> None:
        self._run_qml_probe(
            "inactive-input-port-ux-host",
            """
            payload = node_payload()
            payload["ports"][0]["key"] = "path"
            payload["ports"][0]["label"] = "path"
            payload["ports"][0]["kind"] = "data"
            payload["ports"][0]["data_type"] = "path"
            payload["ports"][0]["inactive"] = True
            payload["ports"][0]["inactive_source_key"] = "result_file"
            payload["ports"][0]["inactive_reason"] = "Driven by result_file"

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            inactive_slash = named_child_items(host, "graphNodeInputPortInactiveSlash")[0]
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            input_mouse = named_child_items(host, "graphNodeInputPortMouseArea")[0]

            assert abs(float(input_dot.property("opacity")) - 0.46) < 0.01
            assert abs(float(input_label.property("opacity")) - 0.52) < 0.01
            assert bool(inactive_slash.property("visible"))
            assert input_mouse.property("inactiveTooltipText") == "Driven by result_file"
            assert input_mouse.property("cursorShape") == Qt.CursorShape.ForbiddenCursor
            """,
        )

    def test_flowchart_host_does_not_replace_surface_suppressed_labels_with_tooltips(self) -> None:
        self._run_qml_probe(
            "flowchart-no-tooltip-port-labels-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": flowchart_payload("decision"),
                    "showPortLabelsPreference": False,
                },
            )

            assert not bool(host.property("_portLabelsVisible"))
            assert not bool(host.property("_tooltipOnlyPortLabelsActive"))
            assert not bool(host.property("_usesStandardPortLabelColumns"))
            """,
        )

    def test_standard_exec_ports_remain_visible_without_hover(self) -> None:
        self._run_qml_probe(
            "standard-exec-port-visible-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            output_dot = named_child_items(host, "graphNodeOutputPortDot")[0]

            assert float(input_dot.property("opacity")) > 0.99
            assert float(output_dot.property("opacity")) > 0.99
            """,
        )

    def test_flow_edge_ports_reveal_on_hover_and_pending_connection_only(self) -> None:
        self._run_qml_probe(
            "flow-edge-port-reveal-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": flowchart_payload("decision")},
            )
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            output_dot = named_child_items(host, "graphNodeOutputPortDot")[0]

            assert float(input_dot.property("opacity")) < 0.01
            assert float(output_dot.property("opacity")) < 0.01

            host.setProperty("pendingPort", {
                "node_id": "node_surface_host_test",
                "port_key": "top",
                "direction": "neutral",
            })
            app.processEvents()

            assert float(input_dot.property("opacity")) > 0.99
            assert float(output_dot.property("opacity")) < 0.01

            host.setProperty("pendingPort", None)
            app.processEvents()

            assert float(input_dot.property("opacity")) < 0.01
            assert float(output_dot.property("opacity")) < 0.01

            window = attach_host_to_window(host)
            try:
                hover_host_local_point(window, host, float(host.width()) * 0.5, float(host.height()) * 0.5)
                assert bool(host.property("hoverActive"))
                assert float(input_dot.property("opacity")) > 0.99
                assert float(output_dot.property("opacity")) > 0.99
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_graph_node_host_exposes_split_helper_layers_with_stable_stacking(self) -> None:
        self._run_qml_probe(
            "host-split-helper-layers",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            header_layer = host.findChild(QObject, "graphNodeHeaderLayer")
            gesture_layer = host.findChild(QObject, "graphNodeHostGestureLayer")
            ports_layer = host.findChild(QObject, "graphNodePortsLayer")
            resize_handles = named_child_items(host, "graphNodeResizeHandle")
            drag_area = host.findChild(QObject, "graphNodeDragArea")
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")

            assert background_layer is not None
            assert header_layer is not None
            assert gesture_layer is not None
            assert ports_layer is not None
            assert len(resize_handles) == 4
            assert {str(handle.property("cornerRole")) for handle in resize_handles} == {
                "topLeft",
                "topRight",
                "bottomLeft",
                "bottomRight",
            }
            assert loader is not None
            assert drag_area is not None
            assert drag_area.parentItem().objectName() == "graphNodeHostGestureLayer"

            surface_layer = loader.parentItem()
            assert surface_layer is not None
            assert float(background_layer.property("z")) < float(surface_layer.property("z"))
            assert float(gesture_layer.property("z")) < float(surface_layer.property("z"))
            assert float(header_layer.property("z")) > float(surface_layer.property("z"))
            assert float(ports_layer.property("z")) > float(header_layer.property("z"))
            assert all(float(handle.property("z")) > float(ports_layer.property("z")) for handle in resize_handles)
            """,
        )

    def test_graph_node_host_shadow_cache_key_ignores_viewport_cache_flags_but_tracks_geometry_and_shadow_preferences(self) -> None:
        self._run_qml_probe(
            "host-shadow-cache-key",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": node_payload(),
                    "showShadow": True,
                },
            )
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            shadow_item = host.findChild(QObject, "graphNodeShadow")
            chrome_item = host.findChild(QObject, "graphNodeChrome")

            assert background_layer is not None
            assert shadow_item is not None
            assert chrome_item is not None
            assert bool(background_layer.property("cacheActive"))
            assert bool(background_layer.property("chromeCacheActive"))
            assert bool(background_layer.property("shadowCacheActive"))
            assert bool(chrome_item.property("visible"))
            assert bool(shadow_item.property("cached"))

            baseline_key = str(background_layer.property("cacheKey") or "")
            assert baseline_key

            host.setProperty("viewportInteractionCacheActive", True)
            app.processEvents()
            assert str(background_layer.property("cacheKey") or "") == baseline_key

            host.setProperty("snapshotReuseActive", True)
            app.processEvents()
            assert str(background_layer.property("cacheKey") or "") == baseline_key

            host.setProperty("_liveWidth", 244.0)
            host.setProperty("_liveHeight", 96.0)
            host.setProperty("_liveGeometryActive", True)
            app.processEvents()
            geometry_key = str(background_layer.property("cacheKey") or "")
            assert geometry_key != baseline_key

            host.setProperty("_liveGeometryActive", False)
            host.setProperty("shadowStrength", 55)
            app.processEvents()
            shadow_preference_key = str(background_layer.property("cacheKey") or "")
            assert shadow_preference_key != baseline_key
            assert shadow_preference_key != geometry_key
            """,
        )

    def test_graph_node_host_node_execution_visualization_states_drive_timer_priority_and_cache_keys(self) -> None:
        self._run_qml_probe(
            "host-node-execution-visualization",
            """
            from PyQt6.QtCore import pyqtProperty, pyqtSignal
            from PyQt6.QtTest import QTest

            class ExecutionSceneBridge(QObject):
                selected_node_lookup_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._selected_node_lookup = {}

                @pyqtProperty("QVariantMap", notify=selected_node_lookup_changed)
                def selected_node_lookup(self):
                    return dict(self._selected_node_lookup)

            class ExecutionCanvasItem(QQuickItem):
                failed_node_lookup_changed = pyqtSignal()
                failed_node_revision_changed = pyqtSignal()
                running_node_lookup_changed = pyqtSignal()
                completed_node_lookup_changed = pyqtSignal()
                node_execution_revision_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._scene_bridge = ExecutionSceneBridge()
                    self._failed_node_lookup = {}
                    self._failed_node_revision = 0
                    self._running_node_lookup = {"node_surface_host_test": True}
                    self._completed_node_lookup = {}
                    self._node_execution_revision = 1

                @pyqtProperty(QObject, constant=True)
                def sceneBridge(self):
                    return self._scene_bridge

                @pyqtProperty("QVariantMap", notify=failed_node_lookup_changed)
                def failedNodeLookup(self):
                    return dict(self._failed_node_lookup)

                @pyqtProperty(int, notify=failed_node_revision_changed)
                def failedNodeRevision(self):
                    return int(self._failed_node_revision)

                @pyqtProperty("QVariantMap", notify=running_node_lookup_changed)
                def runningNodeLookup(self):
                    return dict(self._running_node_lookup)

                @pyqtProperty("QVariantMap", notify=completed_node_lookup_changed)
                def completedNodeLookup(self):
                    return dict(self._completed_node_lookup)

                @pyqtProperty(int, notify=node_execution_revision_changed)
                def nodeExecutionRevision(self):
                    return int(self._node_execution_revision)

                def set_running(self, node_id):
                    self._running_node_lookup = {str(node_id): True}
                    self._completed_node_lookup = {}
                    self._node_execution_revision += 1
                    self.running_node_lookup_changed.emit()
                    self.completed_node_lookup_changed.emit()
                    self.node_execution_revision_changed.emit()

                def set_completed(self, node_id):
                    self._running_node_lookup = {}
                    self._completed_node_lookup = {str(node_id): True}
                    self._node_execution_revision += 1
                    self.running_node_lookup_changed.emit()
                    self.completed_node_lookup_changed.emit()
                    self.node_execution_revision_changed.emit()

                def set_failed(self, node_id):
                    self._failed_node_lookup = {str(node_id): True}
                    self._failed_node_revision += 1
                    self.failed_node_lookup_changed.emit()
                    self.failed_node_revision_changed.emit()

            canvas_item = ExecutionCanvasItem()
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": node_payload(),
                    "canvasItem": canvas_item,
                    "showShadow": True,
                },
            )
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            running_halo = host.findChild(QObject, "graphNodeRunningHalo")
            running_pulse_halo = host.findChild(QObject, "graphNodeRunningPulseHalo")
            completed_flash_halo = host.findChild(QObject, "graphNodeCompletedFlashHalo")
            elapsed_timer = host.findChild(QObject, "graphNodeElapsedTimer")

            assert background_layer is not None
            assert running_halo is not None
            assert running_pulse_halo is not None
            assert completed_flash_halo is not None
            assert elapsed_timer is not None

            app.processEvents()
            assert bool(host.property("isRunningNode"))
            assert not bool(host.property("isCompletedNode"))
            assert bool(host.property("renderActive"))
            assert int(host.property("z")) == 31
            assert str(background_layer.property("effectiveBorderState")) == "running"
            assert bool(running_halo.property("visible"))
            assert bool(running_pulse_halo.property("visible"))
            assert bool(elapsed_timer.property("visible"))
            running_key = str(background_layer.property("cacheKey") or "")
            assert "|running|" in running_key

            QTest.qWait(160)
            app.processEvents()
            assert str(elapsed_timer.property("text") or "") != "0.0s"

            canvas_item.set_completed("node_surface_host_test")
            app.processEvents()
            QTest.qWait(80)
            app.processEvents()

            assert not bool(host.property("isRunningNode"))
            assert bool(host.property("isCompletedNode"))
            assert bool(host.property("renderActive"))
            assert int(host.property("z")) == 29
            assert str(background_layer.property("effectiveBorderState")) == "completed"
            assert not bool(running_halo.property("visible"))
            assert not bool(running_pulse_halo.property("visible"))
            assert not bool(elapsed_timer.property("visible"))
            assert float(background_layer.property("completedFlashProgress")) > 0.0
            completed_key = str(background_layer.property("cacheKey") or "")
            assert completed_key != running_key
            assert "|completed|" in completed_key

            canvas_item.set_failed("node_surface_host_test")
            app.processEvents()

            assert bool(host.property("isFailedNode"))
            assert str(background_layer.property("effectiveBorderState")) == "failed"
            assert not bool(running_halo.property("visible"))
            assert not bool(running_pulse_halo.property("visible"))
            assert not bool(completed_flash_halo.property("visible"))
            assert "|failed|" in str(background_layer.property("cacheKey") or "")
            """,
        )

    def test_flowchart_host_shadow_visibility_follows_global_shadow_preference(self) -> None:
        self._run_qml_probe(
            "flowchart-host-shadow-visibility",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": flowchart_payload("decision"),
                    "showShadow": True,
                },
            )
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            shadow_item = host.findChild(QObject, "graphNodeShadow")
            flowchart_shadow = host.findChild(QObject, "graphNodeFlowchartShadow")
            chrome_item = host.findChild(QObject, "graphNodeChrome")
            flowchart_surface = host.findChild(QObject, "graphNodeFlowchartSurface")

            assert bool(host.property("isFlowchartSurface"))
            assert not bool(host.property("_useHostChrome"))
            assert background_layer is not None
            assert shadow_item is not None
            assert flowchart_shadow is not None
            assert chrome_item is not None
            assert flowchart_surface is not None
            assert not bool(background_layer.property("cacheActive"))
            assert not bool(background_layer.property("chromeCacheActive"))
            assert not bool(background_layer.property("shadowCacheActive"))
            assert not bool(chrome_item.property("visible"))
            assert not bool(shadow_item.property("visible"))
            assert bool(flowchart_surface.property("shapeShadowVisible"))
            assert bool(flowchart_surface.property("shapeShadowCacheActive"))
            assert bool(flowchart_shadow.property("visible"))
            assert bool(flowchart_shadow.property("cacheActive"))

            host.setProperty("showShadow", False)
            app.processEvents()

            assert not bool(background_layer.property("cacheActive"))
            assert not bool(background_layer.property("shadowCacheActive"))
            assert not bool(shadow_item.property("visible"))
            assert not bool(flowchart_surface.property("shapeShadowVisible"))
            assert not bool(flowchart_surface.property("shapeShadowCacheActive"))
            assert not bool(flowchart_shadow.property("visible"))
            """,
        )

    def test_flowchart_host_shadow_cache_key_tracks_shadow_preferences_without_host_chrome(self) -> None:
        self._run_qml_probe(
            "flowchart-host-shadow-cache-key",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": flowchart_payload("decision"),
                    "showShadow": True,
                },
            )
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            shadow_item = host.findChild(QObject, "graphNodeShadow")
            flowchart_shadow = host.findChild(QObject, "graphNodeFlowchartShadow")
            chrome_item = host.findChild(QObject, "graphNodeChrome")
            flowchart_surface = host.findChild(QObject, "graphNodeFlowchartSurface")

            assert background_layer is not None
            assert shadow_item is not None
            assert flowchart_shadow is not None
            assert chrome_item is not None
            assert flowchart_surface is not None
            assert not bool(background_layer.property("cacheActive"))
            assert not bool(background_layer.property("chromeCacheActive"))
            assert not bool(background_layer.property("shadowCacheActive"))
            assert not bool(chrome_item.property("visible"))
            assert not bool(shadow_item.property("visible"))
            assert bool(flowchart_shadow.property("cacheActive"))

            baseline_key = str(flowchart_shadow.property("cacheKey") or "")
            assert baseline_key

            host.setProperty("viewportInteractionCacheActive", True)
            app.processEvents()
            assert str(flowchart_shadow.property("cacheKey") or "") == baseline_key

            host.setProperty("snapshotReuseActive", True)
            app.processEvents()
            assert str(flowchart_shadow.property("cacheKey") or "") == baseline_key

            host.setProperty("_liveWidth", 248.0)
            host.setProperty("_liveHeight", 132.0)
            host.setProperty("_liveGeometryActive", True)
            app.processEvents()
            geometry_key = str(flowchart_shadow.property("cacheKey") or "")
            assert geometry_key != baseline_key

            host.setProperty("_liveGeometryActive", False)
            host.setProperty("shadowSoftness", 41)
            app.processEvents()
            shadow_preference_key = str(flowchart_shadow.property("cacheKey") or "")
            assert shadow_preference_key != baseline_key
            assert shadow_preference_key != geometry_key

            host.setProperty("showShadow", False)
            app.processEvents()
            disabled_shadow_key = str(flowchart_shadow.property("cacheKey") or "")
            assert disabled_shadow_key != shadow_preference_key
            assert not bool(background_layer.property("cacheActive"))
            assert not bool(flowchart_shadow.property("cacheActive"))
            """,
        )

    def test_graph_node_host_shows_four_resize_handles_only_on_hover_for_expanded_nodes(self) -> None:
        self._run_qml_probe(
            "host-hover-only-resize-handles",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            resize_handles = named_child_items(host, "graphNodeResizeHandle")
            assert len(resize_handles) == 4
            assert all(not bool(handle.property("visible")) for handle in resize_handles)

            window = attach_host_to_window(host)
            hover_host_local_point(window, host, 84.0, 40.0)

            assert bool(host.property("hoverActive"))
            assert all(bool(handle.property("visible")) for handle in resize_handles)

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_node_host_keeps_resize_handles_hidden_for_collapsed_nodes(self) -> None:
        self._run_qml_probe(
            "host-collapsed-resize-handles-hidden",
            """
            payload = node_payload()
            payload["collapsed"] = True
            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            resize_handles = named_child_items(host, "graphNodeResizeHandle")
            assert len(resize_handles) == 4

            window = attach_host_to_window(host)
            hover_host_local_point(window, host, 24.0, 18.0)

            assert all(not bool(handle.property("visible")) for handle in resize_handles)

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_node_host_top_left_resize_handle_previews_anchored_geometry(self) -> None:
        self._run_qml_probe(
            "host-top-left-resize-preview",
            """
            from PyQt6.QtCore import QPoint
            from PyQt6.QtTest import QTest

            payload = node_payload()
            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            preview_events = []
            finish_events = []
            host.resizePreviewChanged.connect(
                lambda node_id, x, y, width, height, active: preview_events.append(
                    (node_id, x, y, width, height, active)
                )
            )
            host.resizeFinished.connect(
                lambda node_id, x, y, width, height: finish_events.append((node_id, x, y, width, height))
            )

            window = attach_host_to_window(host)
            hover_host_local_point(window, host, 40.0, 24.0)

            top_left_handle = [
                handle
                for handle in named_child_items(host, "graphNodeResizeHandle")
                if str(handle.property("cornerRole")) == "topLeft"
            ][0]
            start_point = item_scene_point(top_left_handle)
            end_point = QPoint(start_point.x() - 30, start_point.y() - 20)

            QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start_point)
            settle_events(2)
            QTest.mouseMove(window, end_point)
            settle_events(2)

            assert bool(host.property("_liveGeometryActive"))
            assert abs(float(host.x()) - 90.0) < 0.75
            assert abs(float(host.y()) - 100.0) < 0.75
            assert abs(float(host.width()) - 240.0) < 0.75
            assert abs(float(host.height()) - 108.0) < 0.75
            assert any(
                entry[0] == "node_surface_host_test"
                and abs(float(entry[1]) - 90.0) < 0.75
                and abs(float(entry[2]) - 100.0) < 0.75
                and abs(float(entry[3]) - 240.0) < 0.75
                and abs(float(entry[4]) - 108.0) < 0.75
                and bool(entry[5])
                for entry in preview_events
            )

            QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end_point)
            settle_events(2)

            assert finish_events == [("node_surface_host_test", 90.0, 100.0, 240.0, 108.0)]
            assert not bool(host.property("_liveGeometryActive"))

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_node_host_routes_body_click_open_and_context_from_below_surface_layer(self) -> None:
        self._run_qml_probe(
            "host-body-interactions-below-surface",
            """
            from PyQt6.QtQml import QQmlProperty

            payload = node_payload()
            payload["inline_properties"] = []
            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            gesture_layer = host.findChild(QObject, "graphNodeHostGestureLayer")
            drag_area = host.findChild(QObject, "graphNodeDragArea")

            assert loader is not None
            assert gesture_layer is not None
            assert drag_area is not None
            assert drag_area.parentItem().objectName() == "graphNodeHostGestureLayer"

            surface_layer = loader.parentItem()
            assert surface_layer is not None
            assert float(surface_layer.property("z")) > float(drag_area.property("z"))
            assert abs(float(drag_area.property("width")) - float(host.property("width"))) < 0.5
            assert abs(float(drag_area.property("height")) - float(host.property("height"))) < 0.5

            drag_target = QQmlProperty.read(drag_area, "drag.target")
            assert drag_target is not None
            assert drag_target.property("objectName") == "graphNodeCard"
            assert drag_target.property("nodeData")["node_id"] == "node_surface_host_test"

            window = attach_host_to_window(host)
            body_point = host_scene_point(host, 105.0, 44.0)
            events = host_pointer_events(host)

            mouse_click(window, body_point)
            assert events["clicked"] == [("node_surface_host_test", False)]

            mouse_double_click(window, body_point)
            assert events["opened"] == ["node_surface_host_test"]

            mouse_click(window, body_point, Qt.MouseButton.RightButton)
            assert len(events["contexts"]) == 1
            assert events["contexts"][0][0] == "node_surface_host_test"
            assert abs(float(events["contexts"][0][1]) - 105.0) < 0.5
            assert abs(float(events["contexts"][0][2]) - 44.0) < 0.5

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_node_card_wrapper_preserves_standard_host_contract(self) -> None:
        self._run_qml_probe(
            "node-card-wrapper",
            """
            node_card = create_component(
                node_card_qml_path,
                {"nodeData": node_payload(surface_family="annotation", surface_variant="sticky_note")},
            )
            assert node_card.objectName() == "graphNodeCard"
            assert node_card.property("surfaceFamily") == "standard"
            assert node_card.findChild(QObject, "graphNodeSurfaceLoader") is not None
            assert node_card.findChild(QObject, "graphNodeStandardSurface") is not None
            """,
        )

    def test_graph_canvas_keeps_graph_node_card_discoverability_through_host_delegate(self) -> None:
        self._run_qml_probe(
            "graph-canvas-host",
            """
            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) >= 1
            assert node_cards[0].findChild(QObject, "graphNodeStandardSurface") is not None
            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_node_host_render_activation_reloads_offscreen_surface_for_hover_drag_and_resize(self) -> None:
        self._run_qml_probe(
            "host-render-activation-force-active-states",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": node_payload(),
                    "renderActivationSceneRectPayload": {
                        "x": -400.0,
                        "y": -300.0,
                        "width": 60.0,
                        "height": 40.0,
                    },
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            settle_events(2)
            assert not bool(host.property("renderActive"))
            assert not bool(loader.property("renderActive"))
            assert not bool(loader.property("surfaceLoaded"))

            host.setProperty("liveDragDx", 18.0)
            settle_events(2)

            assert bool(host.property("renderActive"))
            assert bool(loader.property("renderActive"))
            assert bool(loader.property("surfaceLoaded"))

            host.setProperty("liveDragDx", 0.0)
            settle_events(2)

            assert not bool(host.property("renderActive"))
            assert not bool(loader.property("renderActive"))
            assert not bool(loader.property("surfaceLoaded"))

            host.setProperty("_liveX", 90.0)
            host.setProperty("_liveY", 100.0)
            host.setProperty("_liveWidth", 240.0)
            host.setProperty("_liveHeight", 108.0)
            host.setProperty("_liveGeometryActive", True)
            settle_events(2)

            assert bool(host.property("renderActive"))
            assert bool(loader.property("renderActive"))
            assert bool(loader.property("surfaceLoaded"))

            host.setProperty("_liveGeometryActive", False)
            settle_events(2)

            assert not bool(host.property("renderActive"))
            assert not bool(loader.property("renderActive"))
            assert not bool(loader.property("surfaceLoaded"))

            window = attach_host_to_window(host)
            hover_host_local_point(window, host, 84.0, 40.0)

            assert bool(host.property("hoverActive"))
            assert bool(host.property("renderActive"))
            assert bool(loader.property("renderActive"))
            assert bool(loader.property("surfaceLoaded"))

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_keeps_live_drag_preview_continuous_when_snap_to_grid_is_enabled(self) -> None:
        self._run_qml_probe(
            "graph-canvas-snap-live-preview",
            """
            from PyQt6.QtCore import pyqtProperty, pyqtSignal

            class MainWindowBridge(QObject):
                snap_to_grid_changed = pyqtSignal()
                graphics_preferences_changed = pyqtSignal()

                @pyqtProperty(bool, notify=snap_to_grid_changed)
                def snap_to_grid_enabled(self):
                    return True

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, notify=graphics_preferences_changed)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, notify=graphics_preferences_changed)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, notify=graphics_preferences_changed)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_minimap_expanded(self):
                    return True

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)
            node_id = scene.nodes_model[0]["node_id"]

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)
            main_window_bridge = MainWindowBridge()

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": main_window_bridge,
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]

            assert canvas.snapToGridEnabled() is True
            node_card.dragOffsetChanged.emit(node_id, 11.0, 9.0)
            app.processEvents()
            assert canvas.liveDragDxForNode(node_id) == 11.0
            assert canvas.liveDragDyForNode(node_id) == 9.0

            node_card.dragFinished.emit(node_id, 131.0, 149.0, True)
            app.processEvents()
            assert canvas.liveDragDxForNode(node_id) == 0.0
            assert canvas.liveDragDyForNode(node_id) == 0.0
            assert scene.nodes_model[0]["x"] == 140.0
            assert scene.nodes_model[0]["y"] == 140.0

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_routes_live_resize_geometry_through_edge_layer_and_scene_commit(self) -> None:
        self._run_qml_probe(
            "graph-canvas-live-resize-geometry",
            """
            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            source_node_id = scene.add_node_from_type("core.start", 40.0, 140.0)
            target_node_id = scene.add_node_from_type("core.logger", 220.0, 140.0)
            scene.add_edge(source_node_id, "exec_out", target_node_id, "exec_in")

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            target_card = [
                card
                for card in node_cards
                if card.property("nodeData")["node_id"] == target_node_id
            ][0]
            edge_layer = canvas.findChild(QObject, "graphCanvasEdgeLayer")
            assert edge_layer is not None

            target_card.resizePreviewChanged.emit(target_node_id, 190.0, 120.0, 260.0, 120.0, True)
            app.processEvents()

            canvas_live_geometry = variant_value(canvas.property("liveNodeGeometry"))
            edge_live_geometry = variant_value(edge_layer.property("liveNodeGeometry"))
            assert canvas_live_geometry[target_node_id] == {
                "x": 190.0,
                "y": 120.0,
                "width": 260.0,
                "height": 120.0,
            }
            assert edge_live_geometry[target_node_id] == canvas_live_geometry[target_node_id]

            target_card.resizeFinished.emit(target_node_id, 190.0, 120.0, 260.0, 120.0)
            app.processEvents()

            assert variant_value(canvas.property("liveNodeGeometry")) == {}
            updated_target = [node for node in scene.nodes_model if node["node_id"] == target_node_id][0]
            assert updated_target["x"] == 190.0
            assert updated_target["y"] == 120.0
            assert updated_target["width"] == 260.0
            assert updated_target["height"] == 120.0

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_drag_moves_all_selected_nodes_together(self) -> None:
        self._run_qml_probe(
            "graph-canvas-multi-drag-selection",
            """
            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            first_node_id = scene.add_node_from_type("core.logger", 120.0, 140.0)
            second_node_id = scene.add_node_from_type("core.start", 320.0, 180.0)
            scene.select_node(first_node_id, False)
            scene.select_node(second_node_id, True)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = {
                card.property("nodeData")["node_id"]: card
                for card in named_child_items(canvas, "graphNodeCard")
            }
            assert set(scene.selected_node_lookup) == {first_node_id, second_node_id}
            drag_node_ids = canvas.dragNodeIdsForAnchor(second_node_id)
            if hasattr(drag_node_ids, "toVariant"):
                drag_node_ids = drag_node_ids.toVariant()
            assert list(drag_node_ids) == [second_node_id, first_node_id]

            before = {item["node_id"]: (item["x"], item["y"]) for item in scene.nodes_model}
            node_cards[second_node_id].dragOffsetChanged.emit(second_node_id, 25.0, 15.0)
            app.processEvents()
            assert canvas.liveDragDxForNode(first_node_id) == 25.0
            assert canvas.liveDragDyForNode(first_node_id) == 15.0
            assert canvas.liveDragDxForNode(second_node_id) == 25.0
            assert canvas.liveDragDyForNode(second_node_id) == 15.0

            node_cards[second_node_id].dragFinished.emit(second_node_id, 345.0, 195.0, True)
            app.processEvents()
            after = {item["node_id"]: (item["x"], item["y"]) for item in scene.nodes_model}

            assert canvas.liveDragDxForNode(first_node_id) == 0.0
            assert canvas.liveDragDyForNode(first_node_id) == 0.0
            assert canvas.liveDragDxForNode(second_node_id) == 0.0
            assert canvas.liveDragDyForNode(second_node_id) == 0.0
            assert after[first_node_id] == (before[first_node_id][0] + 25.0, before[first_node_id][1] + 15.0)
            assert after[second_node_id] == (before[second_node_id][0] + 25.0, before[second_node_id][1] + 15.0)

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_keeps_node_shadow_visible_during_wheel_zoom(self) -> None:
        self._run_qml_probe(
            "graph-canvas-shadow-quality",
            """
            from tests.qt_wait import wait_for_condition_or_raise

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]
            shadow_item = node_card.findChild(QObject, "graphNodeShadow")
            assert shadow_item is not None
            assert not bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert bool(shadow_item.property("visible"))
            assert not bool(canvas.property("interactionActive"))
            assert bool(canvas.property("highQualityRendering"))

            applied = canvas.applyWheelZoom(
                {"x": 640.0, "y": 360.0, "angleDelta": {"y": 120}, "inverted": False}
            )
            assert applied is True
            app.processEvents()
            assert bool(canvas.property("interactionActive"))
            assert bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert not bool(canvas.property("highQualityRendering"))
            assert bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))

            wait_for_condition_or_raise(
                lambda: (
                    not bool(canvas.property("interactionActive"))
                    and bool(canvas.property("highQualityRendering"))
                    and bool(shadow_item.property("visible"))
                ),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for wheel-zoom interaction state to recover.",
            )
            assert not bool(canvas.property("interactionActive"))
            assert not bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_max_performance_degrades_grid_and_minimap_but_preserves_shadows_during_wheel_zoom(self) -> None:
        self._run_qml_probe(
            "graph-canvas-max-performance-wheel-zoom",
            """
            from tests.qt_wait import wait_for_condition_or_raise

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": {
                        "graphics_show_grid": True,
                        "graphics_show_minimap": True,
                        "graphics_minimap_expanded": True,
                        "graphics_node_shadow": True,
                        "graphics_shadow_strength": 70,
                        "graphics_shadow_softness": 50,
                        "graphics_shadow_offset": 4,
                        "graphics_performance_mode": "max_performance",
                        "snap_to_grid_enabled": False,
                        "snap_grid_size": 20.0,
                    },
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]
            shadow_item = node_card.findChild(QObject, "graphNodeShadow")
            background = canvas.findChild(QObject, "graphCanvasBackground")
            minimap_overlay = canvas.findChild(QObject, "graphCanvasMinimapOverlay")
            minimap_viewport = canvas.findChild(QObject, "graphCanvasMinimapViewport")
            assert shadow_item is not None
            assert background is not None
            assert minimap_overlay is not None
            assert minimap_viewport is not None
            assert canvas.property("resolvedGraphicsPerformanceMode") == "max_performance"
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert bool(shadow_item.property("visible"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(background.property("effectiveShowGrid"))
            assert bool(minimap_overlay.property("minimapContentVisible"))
            assert bool(minimap_viewport.property("visible"))

            applied = canvas.applyWheelZoom(
                {"x": 640.0, "y": 360.0, "angleDelta": {"y": 120}, "inverted": False}
            )
            assert applied is True
            app.processEvents()
            assert bool(canvas.property("interactionActive"))
            assert bool(canvas.property("transientDegradedWindowActive"))
            assert not bool(canvas.property("highQualityRendering"))
            assert bool(canvas.property("gridSimplificationActive"))
            assert bool(canvas.property("minimapSimplificationActive"))
            assert not bool(canvas.property("shadowSimplificationActive"))
            assert bool(canvas.property("snapshotProxyReuseActive"))
            assert bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))
            assert not bool(background.property("effectiveShowGrid"))
            assert not bool(minimap_overlay.property("minimapContentVisible"))
            assert not bool(minimap_viewport.property("visible"))

            wait_for_condition_or_raise(
                lambda: (
                    not bool(canvas.property("interactionActive"))
                    and not bool(canvas.property("transientDegradedWindowActive"))
                    and bool(canvas.property("highQualityRendering"))
                    and bool(shadow_item.property("visible"))
                    and bool(background.property("effectiveShowGrid"))
                    and bool(minimap_overlay.property("minimapContentVisible"))
                ),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for max-performance wheel-zoom recovery.",
            )
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))
            assert bool(background.property("effectiveShowGrid"))
            assert bool(minimap_overlay.property("minimapContentVisible"))
            assert bool(minimap_viewport.property("visible"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_minimap_keeps_node_geometry_static_when_center_changes(self) -> None:
        self._run_qml_probe(
            "graph-canvas-minimap-center-stability",
            """
            from tests.qt_wait import wait_for_condition_or_raise

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)
            scene.add_node_from_type("core.logger", 460.0, 280.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": {
                        "graphics_show_grid": True,
                        "graphics_show_minimap": True,
                        "graphics_minimap_expanded": True,
                        "graphics_node_shadow": True,
                        "graphics_shadow_strength": 70,
                        "graphics_shadow_softness": 50,
                        "graphics_shadow_offset": 4,
                        "graphics_performance_mode": "full_fidelity",
                        "snap_to_grid_enabled": False,
                        "snap_grid_size": 20.0,
                    },
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            minimap_viewport = canvas.findChild(QObject, "graphCanvasMinimapViewport")
            minimap_viewport_rect = canvas.findChild(QObject, "graphCanvasMinimapViewportRect")
            minimap_node_content = canvas.findChild(QObject, "graphCanvasMinimapNodeContent")
            assert minimap_viewport is not None
            assert minimap_viewport_rect is not None
            assert minimap_node_content is not None

            wait_for_condition_or_raise(
                lambda: int(minimap_viewport.property("_nodeDelegateCreationCount")) == 2,
                timeout_ms=120,
                app=app,
                timeout_message="Timed out waiting for minimap node delegates to settle.",
            )

            baseline_node_key = str(minimap_viewport.property("nodeGeometryCacheKey"))
            baseline_creation_count = int(minimap_viewport.property("_nodeDelegateCreationCount"))
            baseline_node_x = float(minimap_node_content.property("x"))
            baseline_node_y = float(minimap_node_content.property("y"))
            baseline_node_scale = float(minimap_node_content.property("scale"))
            baseline_rect_key = str(minimap_viewport_rect.property("geometryKey"))
            baseline_rect_updates = int(minimap_viewport_rect.property("_geometryUpdateCount"))

            view.centerOn(160.0, 80.0)
            app.processEvents()
            view.centerOn(260.0, 210.0)
            app.processEvents()

            assert str(minimap_viewport.property("nodeGeometryCacheKey")) == baseline_node_key
            assert int(minimap_viewport.property("_nodeDelegateCreationCount")) == baseline_creation_count
            assert abs(float(minimap_node_content.property("x")) - baseline_node_x) < 0.001
            assert abs(float(minimap_node_content.property("y")) - baseline_node_y) < 0.001
            assert abs(float(minimap_node_content.property("scale")) - baseline_node_scale) < 1e-6
            assert str(minimap_viewport_rect.property("geometryKey")) != baseline_rect_key
            assert int(minimap_viewport_rect.property("_geometryUpdateCount")) > baseline_rect_updates

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_media_performance_mode_keeps_full_surface_during_wheel_zoom_and_recovers(self) -> None:
        self._run_qml_probe(
            "graph-canvas-media-max-performance-wheel-cache",
            """
            import tempfile

            from PyQt6.QtGui import QColor, QImage
            from tests.qt_wait import wait_for_condition_or_raise

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "canvas-proxy-image.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                model = GraphModel()
                registry = build_default_registry()
                workspace_id = model.active_workspace.workspace_id
                scene = GraphSceneBridge()
                scene.set_workspace(model, registry, workspace_id)
                node_id = scene.add_node_from_type("passive.media.image_panel", 120.0, 140.0)
                scene.set_node_property(node_id, "source_path", str(image_path))
                scene.set_node_property(node_id, "caption", "Proxy preview")
                scene.set_node_property(node_id, "fit_mode", "contain")

                view = ViewportBridge()
                view.set_viewport_size(1280.0, 720.0)

                canvas = create_component(
                    graph_canvas_qml_path,
                    {
                        "mainWindowBridge": {
                            "graphics_show_grid": True,
                            "graphics_show_minimap": True,
                            "graphics_minimap_expanded": True,
                            "graphics_node_shadow": True,
                            "graphics_shadow_strength": 70,
                            "graphics_shadow_softness": 50,
                            "graphics_shadow_offset": 4,
                            "graphics_performance_mode": "max_performance",
                            "snap_to_grid_enabled": False,
                            "snap_grid_size": 20.0,
                        },
                        "sceneBridge": scene,
                        "viewBridge": view,
                        "width": 1280.0,
                        "height": 720.0,
                    },
                )
                node_cards = [
                    card for card in named_child_items(canvas, "graphNodeCard")
                    if str(card.property("surfaceFamily")) == "media"
                ]
                assert len(node_cards) == 1

                node_card = node_cards[0]
                loader = node_card.findChild(QObject, "graphNodeSurfaceLoader")
                surface = node_card.findChild(QObject, "graphNodeMediaSurface")
                proxy_preview = node_card.findChild(QObject, "graphNodeMediaProxyPreview")
                applied_viewport = node_card.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                assert loader is not None
                assert surface is not None
                assert proxy_preview is not None
                assert applied_viewport is not None

                wait_for_condition_or_raise(
                    lambda: str(surface.property("previewState")) == "ready",
                    timeout_ms=600,
                    app=app,
                    timeout_message="Timed out waiting for media preview to reach ready state.",
                )
                assert node_card.property("resolvedQualityTier") == "full"
                assert not bool(node_card.property("proxySurfaceRequested"))
                assert not bool(surface.property("proxySurfaceActive"))
                assert not bool(loader.property("proxySurfaceActive"))
                assert not bool(proxy_preview.property("visible"))
                assert bool(applied_viewport.property("visible"))

                applied = canvas.applyWheelZoom(
                    {"x": 640.0, "y": 360.0, "angleDelta": {"y": 120}, "inverted": False}
                )
                assert applied is True

                wait_for_condition_or_raise(
                    lambda: (
                        bool(canvas.property("transientDegradedWindowActive"))
                        and bool(node_card.property("viewportInteractionCacheActive"))
                        and not bool(node_card.property("snapshotReuseActive"))
                        and node_card.property("resolvedQualityTier") == "full"
                        and not bool(node_card.property("proxySurfaceRequested"))
                        and not bool(surface.property("proxySurfaceActive"))
                        and not bool(loader.property("proxySurfaceActive"))
                        and not bool(proxy_preview.property("visible"))
                        and bool(applied_viewport.property("visible"))
                    ),
                    timeout_ms=240,
                    app=app,
                    timeout_message="Timed out waiting for media viewport cache activation.",
                )

                wait_for_condition_or_raise(
                    lambda: (
                        not bool(canvas.property("interactionActive"))
                        and not bool(canvas.property("transientDegradedWindowActive"))
                        and not bool(node_card.property("viewportInteractionCacheActive"))
                        and node_card.property("resolvedQualityTier") == "full"
                        and not bool(node_card.property("proxySurfaceRequested"))
                        and not bool(surface.property("proxySurfaceActive"))
                        and not bool(loader.property("proxySurfaceActive"))
                        and not bool(proxy_preview.property("visible"))
                        and bool(applied_viewport.property("visible"))
                    ),
                    timeout_ms=400,
                    app=app,
                    timeout_message="Timed out waiting for media viewport cache recovery.",
                )

                canvas.deleteLater()
                app.processEvents()
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_graph_canvas_media_performance_mode_uses_proxy_surface_during_mutation_burst_and_recovers(self) -> None:
        self._run_qml_probe(
            "graph-canvas-media-max-performance-mutation-proxy",
            """
            import tempfile

            from PyQt6.QtGui import QColor, QImage
            from tests.qt_wait import wait_for_condition_or_raise

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "canvas-mutation-proxy-image.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                model = GraphModel()
                registry = build_default_registry()
                workspace_id = model.active_workspace.workspace_id
                scene = GraphSceneBridge()
                scene.set_workspace(model, registry, workspace_id)
                node_id = scene.add_node_from_type("passive.media.image_panel", 120.0, 140.0)
                scene.set_node_property(node_id, "source_path", str(image_path))
                scene.set_node_property(node_id, "caption", "Mutation proxy preview")
                scene.set_node_property(node_id, "fit_mode", "contain")

                view = ViewportBridge()
                view.set_viewport_size(1280.0, 720.0)

                canvas = create_component(
                    graph_canvas_qml_path,
                    {
                        "mainWindowBridge": {
                            "graphics_show_grid": True,
                            "graphics_show_minimap": True,
                            "graphics_minimap_expanded": True,
                            "graphics_node_shadow": True,
                            "graphics_shadow_strength": 70,
                            "graphics_shadow_softness": 50,
                            "graphics_shadow_offset": 4,
                            "graphics_performance_mode": "max_performance",
                            "snap_to_grid_enabled": False,
                            "snap_grid_size": 20.0,
                        },
                        "sceneBridge": scene,
                        "viewBridge": view,
                        "width": 1280.0,
                        "height": 720.0,
                    },
                )
                node_cards = [
                    card for card in named_child_items(canvas, "graphNodeCard")
                    if str(card.property("surfaceFamily")) == "media"
                ]
                assert len(node_cards) == 1

                node_card = node_cards[0]
                loader = node_card.findChild(QObject, "graphNodeSurfaceLoader")
                surface = node_card.findChild(QObject, "graphNodeMediaSurface")
                proxy_preview = node_card.findChild(QObject, "graphNodeMediaProxyPreview")
                applied_viewport = node_card.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                assert loader is not None
                assert surface is not None
                assert proxy_preview is not None
                assert applied_viewport is not None

                wait_for_condition_or_raise(
                    lambda: str(surface.property("previewState")) == "ready",
                    timeout_ms=600,
                    app=app,
                    timeout_message="Timed out waiting for media preview to reach ready state.",
                )
                assert node_card.property("resolvedQualityTier") == "full"
                assert not bool(node_card.property("proxySurfaceRequested"))
                assert not bool(surface.property("proxySurfaceActive"))
                assert not bool(loader.property("proxySurfaceActive"))
                assert not bool(proxy_preview.property("visible"))
                assert bool(applied_viewport.property("visible"))

                scene.add_node_from_type("core.logger", 360.0, 210.0)
                app.processEvents()

                node_cards = [
                    card for card in named_child_items(canvas, "graphNodeCard")
                    if str(card.property("surfaceFamily")) == "media"
                ]
                assert len(node_cards) == 1
                node_card = node_cards[0]
                loader = node_card.findChild(QObject, "graphNodeSurfaceLoader")
                surface = node_card.findChild(QObject, "graphNodeMediaSurface")
                proxy_preview = node_card.findChild(QObject, "graphNodeMediaProxyPreview")
                applied_viewport = node_card.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                assert loader is not None
                assert surface is not None
                assert proxy_preview is not None
                assert applied_viewport is not None

                wait_for_condition_or_raise(
                    lambda: (
                        bool(canvas.property("mutationBurstActive"))
                        and bool(canvas.property("transientDegradedWindowActive"))
                        and not bool(node_card.property("viewportInteractionCacheActive"))
                        and bool(node_card.property("snapshotReuseActive"))
                        and node_card.property("resolvedQualityTier") == "proxy"
                        and bool(node_card.property("proxySurfaceRequested"))
                        and bool(surface.property("proxySurfaceActive"))
                        and bool(loader.property("proxySurfaceActive"))
                        and bool(proxy_preview.property("visible"))
                        and not bool(applied_viewport.property("visible"))
                    ),
                    timeout_ms=240,
                    app=app,
                    timeout_message="Timed out waiting for media mutation proxy activation.",
                )

                wait_for_condition_or_raise(
                    lambda: (
                        not bool(canvas.property("mutationBurstActive"))
                        and not bool(canvas.property("transientDegradedWindowActive"))
                        and not bool(node_card.property("snapshotReuseActive"))
                        and node_card.property("resolvedQualityTier") == "full"
                        and not bool(node_card.property("proxySurfaceRequested"))
                        and not bool(surface.property("proxySurfaceActive"))
                        and not bool(loader.property("proxySurfaceActive"))
                        and not bool(proxy_preview.property("visible"))
                        and bool(applied_viewport.property("visible"))
                    ),
                    timeout_ms=400,
                    app=app,
                    timeout_message="Timed out waiting for media mutation proxy recovery.",
                )

                canvas.deleteLater()
                app.processEvents()
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_graph_canvas_mutation_burst_performance_policy_tracks_scene_changes_and_recovers(self) -> None:
        self._run_qml_probe(
            "graph-canvas-mutation-burst-policy",
            """
            from tests.qt_wait import wait_for_condition_or_raise

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            policy = canvas.findChild(QObject, "graphCanvasPerformancePolicy")
            node_cards = {
                card.property("nodeData")["node_id"]: card
                for card in named_child_items(canvas, "graphNodeCard")
            }
            assert policy is not None
            assert len(node_cards) == 1
            tracked_node_id = next(iter(node_cards))
            shadow_item = node_cards[tracked_node_id].findChild(QObject, "graphNodeShadow")
            assert shadow_item is not None

            assert canvas.property("resolvedGraphicsPerformanceMode") == "full_fidelity"
            assert not bool(canvas.property("mutationBurstActive"))
            assert not bool(canvas.property("transientPerformanceActivityActive"))
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(canvas.property("shadowSimplificationActive"))
            assert bool(shadow_item.property("visible"))

            scene.add_node_from_type("core.logger", 360.0, 210.0)
            app.processEvents()
            node_cards = {
                card.property("nodeData")["node_id"]: card
                for card in named_child_items(canvas, "graphNodeCard")
            }
            shadow_item = node_cards[tracked_node_id].findChild(QObject, "graphNodeShadow")
            assert shadow_item is not None

            assert bool(policy.property("mutationBurstActive"))
            assert bool(canvas.property("mutationBurstActive"))
            assert bool(canvas.property("transientPerformanceActivityActive"))
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(canvas.property("shadowSimplificationActive"))
            assert bool(shadow_item.property("visible"))

            wait_for_condition_or_raise(
                lambda: not bool(canvas.property("mutationBurstActive")) and bool(shadow_item.property("visible")),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for scene mutation burst policy to settle.",
            )
            assert not bool(canvas.property("transientPerformanceActivityActive"))
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(canvas.property("shadowSimplificationActive"))
            assert bool(shadow_item.property("visible"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_max_performance_mutation_burst_uses_snapshot_reuse_and_recovers(self) -> None:
        self._run_qml_probe(
            "graph-canvas-max-performance-mutation-burst",
            """
            from tests.qt_wait import wait_for_condition_or_raise

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": {
                        "graphics_show_grid": True,
                        "graphics_show_minimap": True,
                        "graphics_minimap_expanded": True,
                        "graphics_node_shadow": True,
                        "graphics_shadow_strength": 70,
                        "graphics_shadow_softness": 50,
                        "graphics_shadow_offset": 4,
                        "graphics_performance_mode": "max_performance",
                        "snap_to_grid_enabled": False,
                        "snap_grid_size": 20.0,
                    },
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]
            shadow_item = node_card.findChild(QObject, "graphNodeShadow")
            background = canvas.findChild(QObject, "graphCanvasBackground")
            minimap_overlay = canvas.findChild(QObject, "graphCanvasMinimapOverlay")
            minimap_viewport = canvas.findChild(QObject, "graphCanvasMinimapViewport")
            assert shadow_item is not None
            assert background is not None
            assert minimap_overlay is not None
            assert minimap_viewport is not None

            assert canvas.property("resolvedGraphicsPerformanceMode") == "max_performance"
            assert not bool(canvas.property("mutationBurstActive"))
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))

            scene.add_node_from_type("core.logger", 360.0, 210.0)
            app.processEvents()

            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 2
            node_card = node_cards[0]
            shadow_item = node_card.findChild(QObject, "graphNodeShadow")
            assert shadow_item is not None
            assert bool(canvas.property("mutationBurstActive"))
            assert bool(canvas.property("transientPerformanceActivityActive"))
            assert bool(canvas.property("transientDegradedWindowActive"))
            assert not bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert bool(node_card.property("snapshotReuseActive"))
            assert bool(node_card.property("effectiveTextureCacheActive"))
            assert not bool(shadow_item.property("visible"))
            assert not bool(background.property("effectiveShowGrid"))
            assert not bool(minimap_overlay.property("minimapContentVisible"))
            assert not bool(minimap_viewport.property("visible"))

            wait_for_condition_or_raise(
                lambda: (
                    not bool(canvas.property("mutationBurstActive"))
                    and not bool(canvas.property("transientDegradedWindowActive"))
                    and bool(canvas.property("highQualityRendering"))
                    and bool(shadow_item.property("visible"))
                    and bool(background.property("effectiveShowGrid"))
                    and bool(minimap_overlay.property("minimapContentVisible"))
                ),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for max-performance mutation burst recovery.",
            )
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))
            assert bool(background.property("effectiveShowGrid"))
            assert bool(minimap_overlay.property("minimapContentVisible"))
            assert bool(minimap_viewport.property("visible"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_viewport_interaction_cache_remains_viewport_only_not_port_drag(self) -> None:
        self._run_qml_probe(
            "graph-canvas-cache-scope",
            """
            from PyQt6.QtCore import QPointF

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]
            node_payload = node_card.property("nodeData")
            output_dot = named_child_items(node_card, "graphNodeOutputPortDot")[0]
            dot_center = output_dot.mapToItem(
                canvas,
                QPointF(output_dot.width() * 0.5, output_dot.height() * 0.5),
            )
            scene_x = canvas.screenToSceneX(dot_center.x())
            scene_y = canvas.screenToSceneY(dot_center.y())

            assert not bool(canvas.property("interactionActive"))
            assert not bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))

            canvas.beginPortWireDrag(
                str(node_payload["node_id"]),
                "exec_out",
                "out",
                scene_x,
                scene_y,
                dot_center.x(),
                dot_center.y(),
            )
            app.processEvents()

            assert canvas.property("wireDragState") is not None
            assert not bool(canvas.property("interactionActive"))
            assert not bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))

            assert canvas.cancelWireDrag() is True
            app.processEvents()
            assert canvas.property("wireDragState") is None

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_media_crop_mode_locks_host_drag_resize_and_ports(self) -> None:
        self._run_qml_probe(
            "media-host-lock",
            """
            import tempfile
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-lock.png"
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
                assert surface is not None
                assert loader is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break

                surface.setProperty("cropModeActive", True)
                app.processEvents()

                drag_area = host.findChild(QObject, "graphNodeDragArea")
                resize_area = host.findChild(QObject, "graphNodeResizeDragArea")
                input_areas = named_child_items(host, "graphNodeInputPortMouseArea")
                output_areas = named_child_items(host, "graphNodeOutputPortMouseArea")
                embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))

                assert bool(host.property("surfaceInteractionLocked"))
                assert bool(loader.property("blocksHostInteraction"))
                assert host.findChild(QObject, "graphNodeSurfaceHoverActionButton") is None
                assert len(embedded_rects) == 10
                assert drag_area is not None
                assert resize_area is not None
                assert not bool(drag_area.property("enabled"))
                assert not bool(resize_area.property("enabled"))
                assert len(input_areas) >= 1
                assert len(output_areas) >= 1
                assert not bool(input_areas[0].property("enabled"))
                assert not bool(output_areas[0].property("enabled"))

                handle_areas = named_child_items(host, "graphNodeMediaCropHandleMouseArea")
                handle_lookup = {
                    str(item.property("handleId")): item
                    for item in handle_areas
                }
                assert len(handle_lookup) == 8
                assert float(handle_lookup["top_left"].property("width")) > 12.0
                assert float(handle_lookup["top_left"].property("height")) > 12.0
                assert handle_lookup["top_left"].property("cursorShape") == Qt.CursorShape.SizeFDiagCursor
                assert handle_lookup["top_right"].property("cursorShape") == Qt.CursorShape.SizeBDiagCursor
                assert handle_lookup["top"].property("cursorShape") == Qt.CursorShape.SizeVerCursor
                assert handle_lookup["left"].property("cursorShape") == Qt.CursorShape.SizeHorCursor
            """,
        )

    def test_media_surface_publishes_direct_crop_button_rect_without_host_hover_proxy(self) -> None:
        self._run_qml_probe(
            "media-direct-crop-button",
            """
            import tempfile
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-hover-action.png"
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
                crop_button = host.findChild(QObject, "graphNodeMediaCropButton")
                assert surface is not None
                assert loader is not None
                assert crop_button is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break
                assert str(surface.property("previewState")) == "ready"

                window = attach_host_to_window(host)

                hover_host_local_point(window, host, 80.0, 44.0)

                embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
                crop_button_rect = crop_button.property("interactiveRect")

                assert host.findChild(QObject, "graphNodeSurfaceHoverActionButton") is None
                assert loader.metaObject().indexOfProperty("hoverActionHitRect") == -1
                assert surface.metaObject().indexOfProperty("hoverActionHitRect") == -1
                assert bool(crop_button.property("visible"))
                assert len(embedded_rects) == 1
                assert abs(rect_field(embedded_rects[0], "x") - rect_field(crop_button_rect, "x")) < 0.5
                assert abs(rect_field(embedded_rects[0], "y") - rect_field(crop_button_rect, "y")) < 0.5
                assert abs(rect_field(embedded_rects[0], "width") - rect_field(crop_button_rect, "width")) < 0.5
                assert abs(rect_field(embedded_rects[0], "height") - rect_field(crop_button_rect, "height")) < 0.5

                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_media_surface_routes_crop_actions_through_canvas_contract(self) -> None:
        self._run_qml_probe(
            "media-canvas-contract",
            """
            import tempfile
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-contract.png"
                image = QImage(40, 20, QImage.Format.Format_ARGB32)
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
                canvas_item = create_surface_canvas_item()
                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": media_payload,
                        "canvasItem": canvas_item,
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                apply_button = host.findChild(QObject, "graphNodeMediaCropApplyButton")
                assert surface is not None
                assert apply_button is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break
                assert str(surface.property("previewState")) == "ready"

                QMetaObject.invokeMethod(surface, "triggerHoverAction")
                app.processEvents()

                assert canvas_item.requested_crop_node_id == "node_surface_host_test"
                assert bool(surface.property("cropModeActive"))

                surface.setProperty("draftCropX", 0.1)
                surface.setProperty("draftCropY", 0.2)
                surface.setProperty("draftCropW", 0.5)
                surface.setProperty("draftCropH", 0.6)
                app.processEvents()

                QMetaObject.invokeMethod(apply_button, "click")
                app.processEvents()

                assert canvas_item.last_committed_node_id == "node_surface_host_test"
                assert abs(float(canvas_item.last_committed_properties["crop_x"]) - 0.1) < 1e-6
                assert abs(float(canvas_item.last_committed_properties["crop_y"]) - 0.2) < 1e-6
                assert abs(float(canvas_item.last_committed_properties["crop_w"]) - 0.5) < 1e-6
                assert abs(float(canvas_item.last_committed_properties["crop_h"]) - 0.6) < 1e-6
                assert not bool(surface.property("cropModeActive"))
            """,
        )

    def test_media_surface_repair_button_relinks_missing_source_through_canvas_contract(self) -> None:
        self._run_qml_probe(
            "media-repair-contract",
            """
            import tempfile

            from PyQt6.QtGui import QColor, QImage
            from PyQt6.QtQuick import QQuickItem

            class RepairCanvasItem(QQuickItem):
                def __init__(self, repaired_path):
                    super().__init__()
                    self.repaired_path = str(repaired_path)
                    self.last_browse_args = None

                @pyqtSlot(str, str, str, result=str)
                def browseNodePropertyPath(self, node_id, key, current_path):
                    self.last_browse_args = (
                        str(node_id),
                        str(key),
                        str(current_path),
                    )
                    return self.repaired_path

            with tempfile.TemporaryDirectory() as temp_dir:
                missing_path = Path(temp_dir) / "missing.png"
                repaired_path = Path(temp_dir) / "repaired.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(repaired_path))

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": str(missing_path),
                    "caption": "",
                    "fit_mode": "contain",
                }
                canvas_item = RepairCanvasItem(repaired_path)
                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": media_payload,
                        "canvasItem": canvas_item,
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                repair_button = host.findChild(QObject, "graphNodeMediaRepairButton")
                issue_badge = host.findChild(QObject, "graphNodeMediaIssueBadge")
                assert surface is not None
                assert repair_button is not None
                assert issue_badge is not None

                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                assert str(surface.property("previewState")) == "error"
                assert bool(repair_button.property("visible"))
                assert bool(issue_badge.property("visible"))

                QMetaObject.invokeMethod(repair_button, "click")
                app.processEvents()

                assert canvas_item.last_browse_args is not None
                assert canvas_item.last_browse_args[0] == "node_surface_host_test"
                assert canvas_item.last_browse_args[1] == "source_path"
                assert canvas_item.last_browse_args[2].startswith("ea-file-repair:")
                assert committed == [("node_surface_host_test", "source_path", str(repaired_path))]
            """,
        )

    def test_media_surface_accepts_managed_source_refs_in_qml_preview_binding(self) -> None:
        self._run_qml_probe(
            "media-managed-source",
            """
            import tempfile

            from PyQt6.QtGui import QColor, QImage

            from ea_node_editor.persistence.artifact_refs import format_managed_artifact_ref
            from ea_node_editor.ui.media_preview_provider import set_media_preview_project_context_provider

            with tempfile.TemporaryDirectory() as temp_dir:
                project_path = Path(temp_dir) / "artifact_demo.sfe"
                managed_image_path = project_path.with_name("artifact_demo.data") / "assets" / "media" / "managed.png"
                managed_image_path.parent.mkdir(parents=True, exist_ok=True)
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(managed_image_path))

                set_media_preview_project_context_provider(
                    lambda: (
                        project_path,
                        {
                            "artifact_store": {
                                "artifacts": {
                                    "managed_image": {"relative_path": "assets/media/managed.png"},
                                }
                            }
                        },
                    )
                )

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": format_managed_artifact_ref("managed_image"),
                    "caption": "",
                    "fit_mode": "contain",
                }
                host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                assert surface is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break

                assert str(surface.property("previewState")) == "ready"
                assert not bool(surface.property("sourceRejected"))
                assert str(surface.property("previewSourceUrl")).startswith("image://local-media-preview/")
                assert "artifact%3A%2F%2Fmanaged_image" in str(surface.property("previewSourceUrl"))
                assert float(surface.property("sourcePixelWidth")) == 24.0
                assert float(surface.property("sourcePixelHeight")) == 18.0
            """,
        )
