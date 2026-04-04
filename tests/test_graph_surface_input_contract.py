from __future__ import annotations

import gc
from pathlib import Path
import re
import textwrap
import unittest
from unittest.mock import patch

import pytest
from PyQt6.QtCore import QEvent, QUrl
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec
from ea_node_editor.graph.file_issue_state import encode_file_repair_request
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.persistence.artifact_refs import format_managed_artifact_ref
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from tests.conftest import ShellTestEnvironment
from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    graph_surface_pointer_audit_failures,
    run_qml_probe,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.xdist_group("p03_graph_surface")


def _flush_qt_events(app) -> None:  # noqa: ANN001
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def _destroy_shell_window(window, app) -> None:  # noqa: ANN001
    if window is None:
        return
    for timer_name in ("metrics_timer", "graph_hint_timer", "autosave_timer"):
        timer = getattr(window, timer_name, None)
        if timer is not None:
            timer.stop()
    window.close()
    quick_widget = getattr(window, "quick_widget", None)
    if quick_widget is not None:
        window.takeCentralWidget()
        quick_widget.setSource(QUrl())
        quick_widget.hide()
        quick_widget.deleteLater()
        window.quick_widget = None
    window.deleteLater()
    _flush_qt_events(app)
    gc.collect()


class _RenderQualityPayloadPlugin:
    def __init__(self, spec: NodeTypeSpec) -> None:
        self._spec = spec

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, _ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult()


class GraphSurfaceInputContractTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        self._run_qml_probe_with_retry(label, body)

    def _run_qml_probe_once(self, label: str, body: str) -> None:
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
            from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
            from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge

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

            def build_canvas_bridges(*, shell_bridge=None, scene_bridge=None, view_bridge=None):
                state_bridge = GraphCanvasStateBridge(
                    shell_window=shell_bridge,
                    scene_bridge=scene_bridge,
                    view_bridge=view_bridge,
                )
                command_bridge = GraphCanvasCommandBridge(
                    shell_window=shell_bridge,
                    scene_bridge=scene_bridge,
                    view_bridge=view_bridge,
                )
                return state_bridge, command_bridge

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

    def _run_qml_probe_with_retry(self, label: str, body: str, *, retries: int = 2) -> None:
        for attempt in range(max(1, int(retries))):
            try:
                self._run_qml_probe_once(label, body)
                return
            except AssertionError as exc:
                if "exit code 3221226505" not in str(exc) or attempt + 1 >= retries:
                    raise

    def _expand_graph_surface_scan_paths(self, paths: list[Path]) -> list[Path]:
        expanded: list[Path] = []
        for path in paths:
            if path.is_dir():
                expanded.extend(sorted(path.rglob("*.qml")))
            else:
                expanded.append(path)
        return expanded

    def _search_graph_surface_pattern(self, pattern: str, paths: list[Path]) -> list[str]:
        compiled = re.compile(pattern)
        matches: list[str] = []
        for path in self._expand_graph_surface_scan_paths(paths):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if compiled.search(line):
                    matches.append(f"{path.relative_to(_REPO_ROOT)}:{line_number}:{line.strip()}")
        return matches

    def _graph_surface_pointer_audit_failures_with_fallback(self) -> list[str]:
        try:
            return graph_surface_pointer_audit_failures()
        except PermissionError as exc:
            if "Access is denied" not in str(exc):
                raise

        graph_dir = _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "graph"
        passive_dir = graph_dir / "passive"
        surface_files = [
            graph_dir / "GraphInlinePropertiesLayer.qml",
            graph_dir / "GraphStandardNodeSurface.qml",
            *sorted(passive_dir.glob("*Surface.qml")),
        ]
        failures: list[str] = []

        hover_proxy_matches = self._search_graph_surface_pattern(
            r"hoverActionHitRect|graphNodeSurfaceHoverActionButton",
            [graph_dir, passive_dir],
        )
        if hover_proxy_matches:
            failures.append(
                "Removed hover-proxy compatibility shims reappeared:\n"
                + "\n".join(hover_proxy_matches)
            )

        tap_handler_matches = self._search_graph_surface_pattern(r"\bTapHandler\s*\{", surface_files)
        if tap_handler_matches:
            failures.append(
                "Unexpected TapHandler usage in graph-surface QML:\n"
                + "\n".join(tap_handler_matches)
            )

        unexpected_mouse_areas: list[str] = []
        for path in surface_files:
            matches = self._search_graph_surface_pattern(r"\bMouseArea\s*\{", [path])
            if not matches:
                continue
            if path.name == "GraphMediaPanelSurface.qml":
                if len(matches) != 1:
                    unexpected_mouse_areas.append(
                        f"{path.relative_to(_REPO_ROOT)}: expected exactly one crop-handle MouseArea, found {len(matches)}"
                    )
                text = path.read_text(encoding="utf-8")
                if 'objectName: "graphNodeMediaCropHandleMouseArea"' not in text:
                    unexpected_mouse_areas.append(
                        f"{path.relative_to(_REPO_ROOT)}: allowed crop-handle MouseArea objectName is missing"
                    )
                if "targetItem: handleMouseArea" not in text:
                    unexpected_mouse_areas.append(
                        f"{path.relative_to(_REPO_ROOT)}: crop-handle MouseArea is no longer tied to GraphSurfaceInteractiveRegion"
                    )
                continue
            unexpected_mouse_areas.extend(matches)

        if unexpected_mouse_areas:
            failures.append(
                "Unexpected raw MouseArea usage in graph-surface QML:\n"
                + "\n".join(unexpected_mouse_areas)
            )

        return failures

    def test_graph_surface_pointer_audit_rejects_hover_proxy_shims_and_untracked_surface_mouse_areas(self) -> None:
        failures = self._graph_surface_pointer_audit_failures_with_fallback()
        if failures:
            self.fail("\n\n".join(failures))

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

    def test_graph_scene_payload_builder_orders_exec_ports_first_within_each_side(self) -> None:
        registry: NodeRegistry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(
            workspace_id,
            "io.excel_read",
            "Excel Read",
            80.0,
            120.0,
        )
        model.add_node(
            workspace_id,
            "io.excel_write",
            "Excel Write",
            280.0,
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

        payloads_by_type = {str(item["type_id"]): item for item in nodes_payload}

        excel_read_ports = payloads_by_type["io.excel_read"]["ports"]
        excel_read_output_keys = [
            str(port["key"])
            for port in excel_read_ports
            if str(port["direction"]) == "out"
        ]
        self.assertEqual(excel_read_output_keys, ["exec_out", "rows"])

        excel_write_ports = payloads_by_type["io.excel_write"]["ports"]
        excel_write_input_keys = [
            str(port["key"])
            for port in excel_write_ports
            if str(port["direction"]) == "in"
        ]
        excel_write_output_keys = [
            str(port["key"])
            for port in excel_write_ports
            if str(port["direction"]) == "out"
        ]
        self.assertEqual(excel_write_input_keys, ["exec_in", "rows", "path"])
        self.assertEqual(excel_write_output_keys, ["exec_out", "written_path"])

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

    def test_graph_node_host_accepts_viewer_surface_family_without_canvas_special_cases(self) -> None:
        self._run_qml_probe(
            "viewer-surface-family-contract",
            """
            payload = node_payload(surface_family="viewer")
            payload["type_id"] = "tests.viewer_surface_contract"
            payload["title"] = "Viewer Contract"
            payload["width"] = 296.0
            payload["height"] = 236.0
            payload["ports"] = [
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
            ]
            payload["inline_properties"] = []
            payload["render_quality"] = {
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            }
            payload["surface_metrics"] = {
                "default_width": 296.0,
                "default_height": 236.0,
                "min_width": 220.0,
                "min_height": 208.0,
                "collapsed_width": 130.0,
                "collapsed_height": 36.0,
                "header_height": 24.0,
                "header_top_margin": 4.0,
                "body_left_margin": 14.0,
                "body_right_margin": 14.0,
                "body_top": 30.0,
                "body_height": 176.0,
                "body_bottom_margin": 12.0,
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
                "show_header_background": True,
                "show_accent_bar": True,
                "use_host_chrome": True,
                "standard_title_full_width": 0.0,
                "standard_left_label_width": 0.0,
                "standard_right_label_width": 0.0,
                "standard_port_gutter": 21.5,
                "standard_center_gap": 24.0,
                "standard_port_label_min_width": 0.0,
            }
            payload["viewer_surface"] = {
                "body_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "proxy_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "live_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "overlay_target": "body",
                "proxy_surface_supported": True,
                "live_surface_supported": True,
            }

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "snapshotReuseActive": True,
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            assert loader is not None
            assert surface is not None

            assert host.property("surfaceFamily") == "viewer"
            assert loader.property("loadedSurfaceKey") == "viewer"
            assert host.property("requestedQualityTier") == "reduced"
            assert host.property("resolvedQualityTier") == "proxy"
            assert bool(surface.property("proxySurfaceActive"))

            contract = variant_value(loader.property("viewerSurfaceContract"))
            assert contract["overlay_target"] == "body"

            live_rect = loader.property("viewerLiveSurfaceRect")
            assert rect_field(live_rect, "x") == float(contract["live_rect"]["x"])
            assert rect_field(live_rect, "y") == float(contract["live_rect"]["y"])
            assert rect_field(live_rect, "width") == float(contract["live_rect"]["width"])
            assert rect_field(live_rect, "height") == float(contract["live_rect"]["height"])
            """,
        )

    def test_viewer_surface_control_rects_flow_through_host_contract(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-contract",
            """
            from PyQt6.QtCore import pyqtSignal

            class ViewerSessionBridgeStub(QObject):
                sessions_changed = pyqtSignal()

                @pyqtProperty("QVariantList", notify=sessions_changed)
                def sessions_model(self):
                    return [
                        {
                            "workspace_id": "ws_main",
                            "node_id": "node_surface_contract_test",
                            "session_id": "session::viewer-surface-pointer",
                            "phase": "open",
                            "request_id": "req::viewer-pointer",
                            "last_command": "open",
                            "last_error": "",
                            "playback_state": "paused",
                            "step_index": 1,
                            "live_policy": "focus_only",
                            "keep_live": False,
                            "cache_state": "proxy_ready",
                            "invalidated_reason": "",
                            "close_reason": "",
                            "data_refs": {},
                            "summary": {
                                "result_name": "Displacement",
                                "set_label": "Set 1",
                                "cache_state": "proxy_ready",
                            },
                            "options": {
                                "live_mode": "proxy",
                                "playback_state": "paused",
                                "step_index": 1,
                                "live_policy": "focus_only",
                                "keep_live": False,
                            },
                        }
                    ]

                @pyqtProperty(str, constant=True)
                def last_error(self):
                    return ""

            bridge = ViewerSessionBridgeStub()
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)

            payload = node_payload(surface_family="viewer")
            payload["type_id"] = "tests.viewer_surface_contract"
            payload["title"] = "Viewer Contract"
            payload["width"] = 296.0
            payload["height"] = 236.0
            payload["ports"] = [
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
            ]
            payload["inline_properties"] = []
            payload["render_quality"] = {
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            }
            payload["surface_metrics"] = {
                "default_width": 296.0,
                "default_height": 236.0,
                "min_width": 220.0,
                "min_height": 208.0,
                "collapsed_width": 130.0,
                "collapsed_height": 36.0,
                "header_height": 24.0,
                "header_top_margin": 4.0,
                "body_left_margin": 14.0,
                "body_right_margin": 14.0,
                "body_top": 30.0,
                "body_height": 176.0,
                "body_bottom_margin": 12.0,
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
                "show_header_background": True,
                "show_accent_bar": True,
                "use_host_chrome": True,
                "standard_title_full_width": 0.0,
                "standard_left_label_width": 0.0,
                "standard_right_label_width": 0.0,
                "standard_port_gutter": 21.5,
                "standard_center_gap": 24.0,
                "standard_port_label_min_width": 0.0,
            }
            payload["viewer_surface"] = {
                "body_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "proxy_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "live_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "overlay_target": "body",
                "proxy_surface_supported": True,
                "live_surface_supported": True,
            }

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            assert loader is not None
            assert surface is not None

            bridge_binding = variant_value(host.property("viewerBridgeBinding"))
            contract = variant_value(host.property("viewerSurfaceContract"))
            control_rects = variant_list(host.property("viewerInteractiveRects"))
            assert bridge_binding["phase"] == "open", bridge_binding
            assert bridge_binding["live_mode"] == "proxy", bridge_binding
            assert contract["bridge_binding"]["phase"] == "open", contract
            assert len(control_rects) == 6, control_rects
            assert len(variant_list(loader.property("embeddedInteractiveRects"))) == 6, variant_list(loader.property("embeddedInteractiveRects"))
            assert len(contract["interactive_rects"]) == 6, contract
            assert contract["interactive_rects"][0]["width"] > 28.0, contract["interactive_rects"]
            assert contract["interactive_rects"][0]["height"] >= 24.0, contract["interactive_rects"]
            assert rect_field(host.property("viewerBodyRect"), "x") == float(contract["body_rect"]["x"]), variant_value(host.property("viewerBodyRect"))
            assert rect_field(host.property("viewerLiveSurfaceRect"), "width") == float(contract["live_rect"]["width"]), variant_value(host.property("viewerLiveSurfaceRect"))
            assert rect_field(host.property("viewerLiveSurfaceRect"), "height") == float(contract["live_rect"]["height"]), variant_value(host.property("viewerLiveSurfaceRect"))
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
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=window_bridge,
                scene_bridge=scene_bridge,
            )
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
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

    def test_graph_canvas_routes_non_scoped_shared_header_title_edits_without_body_pointer_regressions(self) -> None:
        self._run_qml_probe(
            "graph-canvas-shared-header-title-editor",
            """
            from PyQt6.QtCore import QObject, QPointF, pyqtProperty, pyqtSignal, pyqtSlot

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

            scene_bridge = SceneBridgeStub()
            window_bridge = MainWindowBridgeStub()
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=window_bridge,
                scene_bridge=scene_bridge,
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
            try:
                node_card = next((item for item in walk_items(canvas) if item.objectName() == "graphNodeCard"), None)
                assert node_card is not None
                title_item = node_card.findChild(QObject, "graphNodeTitle")
                editor = node_card.findChild(QObject, "graphNodeTitleEditor")
                assert title_item is not None
                assert editor is not None
                assert bool(node_card.property("sharedHeaderTitleEditable"))

                open_requests = []
                node_card.nodeOpenRequested.connect(lambda node_id: open_requests.append(node_id))

                title_point = title_item.mapToItem(
                    node_card,
                    QPointF(float(title_item.width()) * 0.5, float(title_item.height()) * 0.5),
                )
                body_local_x = float(node_card.property("width")) * 0.5
                body_local_y = float(node_card.property("height")) * 0.78

                assert not node_card.requestInlineTitleEditAt(body_local_x, body_local_y)
                assert not bool(editor.property("visible"))
                assert node_card.requestInlineTitleEditAt(title_point.x(), title_point.y())
                settle_events(5)
                assert bool(editor.property("visible"))
                assert open_requests == []
                assert scene_bridge.select_calls == [("node_surface_contract_test", False)]

                assert not node_card.commitInlineTitleEditAt(title_point.x(), title_point.y())
                assert bool(editor.property("visible"))

                scene_bridge.select_calls.clear()
                scene_bridge.set_node_property_calls.clear()
                editor.setProperty("text", " Updated Logger ")
                app.processEvents()
                assert node_card.commitInlineTitleEditAt(body_local_x, body_local_y)
                settle_events(5)

                assert scene_bridge.set_node_property_calls == [
                    ("node_surface_contract_test", "title", "Updated Logger")
                ]
                assert scene_bridge.select_calls == [("node_surface_contract_test", False)]
                assert not bool(editor.property("visible"))
                assert open_requests == []
            finally:
                canvas.deleteLater()
                app.processEvents()
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_graph_canvas_routes_scoped_open_badge_through_request_open_subnode_scope(self) -> None:
        self._run_qml_probe(
            "graph-canvas-scoped-open-badge-route",
            """
            from PyQt6.QtCore import QObject, QPointF, pyqtProperty, pyqtSignal, pyqtSlot

            scoped_payload = node_payload()
            scoped_payload["can_enter_scope"] = True

            class SceneBridgeStub(QObject):
                nodes_changed = pyqtSignal()
                edges_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.set_node_property_calls = []
                    self._nodes_model = [scoped_payload]
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
                    self.scope_open_calls = []

                @pyqtSlot(str, result=bool)
                def request_open_subnode_scope(self, node_id):
                    self.scope_open_calls.append(str(node_id or ""))
                    return True

            scene_bridge = SceneBridgeStub()
            window_bridge = MainWindowBridgeStub()
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=window_bridge,
                scene_bridge=scene_bridge,
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
            try:
                node_card = next((item for item in walk_items(canvas) if item.objectName() == "graphNodeCard"), None)
                assert node_card is not None
                title_item = node_card.findChild(QObject, "graphNodeTitle")
                editor = node_card.findChild(QObject, "graphNodeTitleEditor")
                open_badge = node_card.findChild(QObject, "graphNodeOpenBadge")
                assert title_item is not None
                assert editor is not None
                assert open_badge is not None
                assert bool(node_card.property("sharedHeaderTitleEditable"))

                title_point = title_item.mapToItem(
                    node_card,
                    QPointF(float(title_item.width()) * 0.5, float(title_item.height()) * 0.5),
                )
                open_point = open_badge.mapToItem(
                    node_card,
                    QPointF(float(open_badge.width()) * 0.5, float(open_badge.height()) * 0.5),
                )

                assert not node_card.requestScopeOpenAt(title_point.x(), title_point.y())
                assert node_card.requestInlineTitleEditAt(title_point.x(), title_point.y())
                settle_events(5)

                assert bool(editor.property("visible"))
                assert scene_bridge.select_calls == [("node_surface_contract_test", False)]

                editor.setProperty("text", " Scoped Logger ")
                app.processEvents()
                assert node_card.requestScopeOpenAt(open_point.x(), open_point.y())
                settle_events(5)

                assert scene_bridge.set_node_property_calls == [
                    ("node_surface_contract_test", "title", "Scoped Logger")
                ]
                assert scene_bridge.select_calls == [
                    ("node_surface_contract_test", False),
                    ("node_surface_contract_test", False),
                ]
                assert window_bridge.scope_open_calls == ["node_surface_contract_test"]
                assert not bool(editor.property("visible"))
            finally:
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
        app.setQuitOnLastWindowClosed(False)
        test_env = ShellTestEnvironment()
        test_env.start()
        window = ShellWindow()
        try:
            window.app_preferences_controller.set_source_import_mode("external_link")
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
            self.assertNotIn("artifact_store", window.model.project.metadata)
        finally:
            _destroy_shell_window(window, app)
            test_env.stop()
            _flush_qt_events(app)

    def test_shell_window_browse_node_property_path_stages_managed_copy_and_reuses_artifact_id(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        app.setQuitOnLastWindowClosed(False)
        test_env = ShellTestEnvironment()
        temp_root = test_env.start()
        window = ShellWindow()
        try:
            seed_fixture = _REPO_ROOT / "tests" / "fixtures" / "passive_nodes" / "reference_preview.png"
            replacement_fixture = temp_root / "replacement.png"
            replacement_fixture.write_bytes(b"replacement-image-bytes")
            project_path = temp_root / "managed-seed-demo.sfe"
            managed_image_path = project_path.with_name("managed-seed-demo.data") / "assets" / "media" / "seed.png"
            managed_image_path.parent.mkdir(parents=True, exist_ok=True)
            managed_image_path.write_bytes(seed_fixture.read_bytes())
            managed_ref = format_managed_artifact_ref("managed_image")

            window.project_path = str(project_path)
            window.model.project.metadata = {
                "artifact_store": {
                    "artifacts": {
                        "managed_image": {"relative_path": "assets/media/seed.png"},
                    }
                }
            }

            image_node_id = window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
            self.assertTrue(image_node_id)
            window.scene.set_node_property(image_node_id, "source_path", managed_ref)
            app.processEvents()

            with patch(
                "ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName",
                return_value=(str(replacement_fixture), ""),
            ) as dialog_mock:
                staged_ref = window.browse_node_property_path(image_node_id, "source_path", managed_ref)
                self.assertEqual(staged_ref, "artifact-stage://managed_image")
                self.assertEqual(dialog_mock.call_count, 1)
                self.assertEqual(dialog_mock.call_args.args[2], str(managed_image_path))

            store = ProjectArtifactStore.from_project_metadata(
                project_path=window.project_path,
                project_metadata=window.model.project.metadata,
            )
            staged_path = store.resolve_staged_path(staged_ref)
            self.assertIsNotNone(staged_path)
            assert staged_path is not None
            self.assertTrue(staged_path.exists())
            self.assertEqual(staged_path.read_bytes(), replacement_fixture.read_bytes())

            with patch(
                "ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName",
                return_value=(str(seed_fixture), ""),
            ) as dialog_mock:
                replacement_ref = window.browse_node_property_path(image_node_id, "source_path", staged_ref)
                self.assertEqual(replacement_ref, staged_ref)
                self.assertEqual(dialog_mock.call_count, 1)
                self.assertEqual(dialog_mock.call_args.args[2], str(staged_path))

            store = ProjectArtifactStore.from_project_metadata(
                project_path=window.project_path,
                project_metadata=window.model.project.metadata,
            )
            replacement_path = store.resolve_staged_path(staged_ref)
            self.assertIsNotNone(replacement_path)
            assert replacement_path is not None
            self.assertEqual(replacement_path, staged_path)
            self.assertTrue(replacement_path.exists())
            self.assertEqual(replacement_path.read_bytes(), seed_fixture.read_bytes())
            self.assertEqual(
                window.model.project.metadata["artifact_store"]["staged"],
                {
                    "managed_image": {
                        "relative_path": ".staging/assets/media/managed_image.png",
                    }
                },
            )
        finally:
            _destroy_shell_window(window, app)
            test_env.stop()
            _flush_qt_events(app)

    def test_shell_window_selected_node_property_items_publish_file_issue_payload(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        app.setQuitOnLastWindowClosed(False)
        test_env = ShellTestEnvironment()
        temp_root = test_env.start()
        window = ShellWindow()
        try:
            missing_path = str(temp_root / "missing-input.txt")
            node_id = window.scene.add_node_from_type("io.file_read", x=120.0, y=80.0)
            self.assertTrue(node_id)
            window.scene.set_node_property(node_id, "path", missing_path)
            window.scene.select_node(node_id, False)
            app.processEvents()

            path_item = next(item for item in window.selected_node_property_items if item["key"] == "path")
            self.assertTrue(path_item["file_issue_active"])
            self.assertEqual(path_item["file_issue_kind"], "external_missing")
            self.assertTrue(path_item["file_issue_supports_external_repair"])
            self.assertFalse(path_item["file_issue_supports_managed_repair"])
            self.assertEqual(
                path_item["file_issue_request"],
                encode_file_repair_request(missing_path),
            )
        finally:
            _destroy_shell_window(window, app)
            test_env.stop()
            _flush_qt_events(app)


if __name__ == "__main__":
    unittest.main()
