from __future__ import annotations

import unittest

from tests.main_window_shell.bridge_contracts import _REPO_ROOT


class ShellLibraryBridgeQmlBoundaryTests(unittest.TestCase):
    def test_owned_qml_components_route_migrated_concerns_through_shell_library_bridge(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.set_library_query",
                    "mainWindowRef.grouped_node_library_items",
                    "mainWindowRef.request_add_node_from_library",
                    "target: root.mainWindowRef",
                ),
                ("shellLibraryBridgeRef",),
            ),
            "ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.request_rename_custom_workflow_from_library",
                    "mainWindowRef.request_set_custom_workflow_scope",
                    "mainWindowRef.request_delete_custom_workflow_from_library",
                ),
                ("shellLibraryBridgeRef",),
            ),
            "ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.graph_search_",
                    "mainWindowRef.set_graph_search_query",
                    "mainWindowRef.request_graph_search_",
                    "target: root.mainWindowRef",
                ),
                ("shellLibraryBridgeRef",),
            ),
            "ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.connection_quick_insert_",
                    "mainWindowRef.set_connection_quick_insert_query",
                    "mainWindowRef.request_close_connection_quick_insert",
                    "mainWindowRef.request_connection_quick_insert_",
                    "target: root.mainWindowRef",
                ),
                ("shellLibraryBridgeRef",),
            ),
            "ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.graph_hint_",
                ),
                ("shellLibraryBridgeRef",),
            ),
        }

        for relative_path, (absent_snippets, present_snippets) in expectations.items():
            qml_path = _REPO_ROOT / relative_path
            qml_text = qml_path.read_text(encoding="utf-8")

            for snippet in absent_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="absent"):
                    self.assertNotIn(snippet, qml_text)

            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="present"):
                    self.assertIn(snippet, qml_text)


class ShellInspectorBridgeQmlBoundaryTests(unittest.TestCase):
    def test_inspector_pane_routes_owned_concerns_through_shell_inspector_bridge(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/shell/InspectorPane.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.has_selected_node",
                    "mainWindowRef.selected_node_is_subnode_pin",
                    "mainWindowRef.selected_node_is_subnode_shell",
                    "mainWindowRef.selected_node_port_items",
                    "mainWindowRef.selected_node_title",
                    "mainWindowRef.selected_node_subtitle",
                    "mainWindowRef.selected_node_collapsible",
                    "mainWindowRef.selected_node_collapsed",
                    "mainWindowRef.selected_node_header_items",
                    "mainWindowRef.selected_node_property_items",
                    "mainWindowRef.pin_data_type_options",
                    "mainWindowRef.request_add_selected_subnode_pin",
                    "mainWindowRef.set_selected_port_label",
                    "mainWindowRef.request_remove_selected_port",
                    "mainWindowRef.set_selected_node_collapsed",
                    "mainWindowRef.request_ungroup_selected_nodes",
                    "mainWindowRef.set_selected_node_property",
                    "mainWindowRef.browse_selected_node_property_path",
                    "mainWindowRef.set_selected_port_exposed",
                    "target: root.mainWindowRef",
                ),
                (
                    "readonly property var inspectorBridgeRef: shellInspectorBridge",
                    "root.inspectorBridgeRef.has_selected_node",
                    "root.inspectorBridgeRef.selected_node_is_subnode_pin",
                    "root.inspectorBridgeRef.selected_node_is_subnode_shell",
                    "root.inspectorBridgeRef.selected_node_port_items",
                    "root.inspectorBridgeRef.selected_node_title",
                    "root.inspectorBridgeRef.selected_node_subtitle",
                    "root.inspectorBridgeRef.selected_node_collapsible",
                    "root.inspectorBridgeRef.selected_node_collapsed",
                    "root.inspectorBridgeRef.selected_node_header_items",
                    "root.inspectorBridgeRef.selected_node_property_items",
                    "root.inspectorBridgeRef.pin_data_type_options",
                    "root.inspectorBridgeRef.request_add_selected_subnode_pin",
                    "root.inspectorBridgeRef.set_selected_port_label",
                    "root.inspectorBridgeRef.request_remove_selected_port",
                    "target: root.inspectorBridgeRef",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/InspectorNodeDefinitionSection.qml": (
                (
                    "mainWindowRef.set_selected_node_collapsed",
                    "mainWindowRef.request_ungroup_selected_nodes",
                ),
                (
                    "definitionSection.pane.inspectorBridgeRef.set_selected_node_collapsed",
                    "definitionSection.pane.inspectorBridgeRef.request_ungroup_selected_nodes",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/InspectorPropertyEditor.qml": (
                (
                    "mainWindowRef.set_selected_node_property",
                    "mainWindowRef.browse_selected_node_property_path",
                ),
                (
                    "propertyEditor.pane.inspectorBridgeRef.set_selected_node_property",
                    "propertyEditor.pane.inspectorBridgeRef.browse_selected_node_property_path",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/InspectorPortRow.qml": (
                ("mainWindowRef.set_selected_port_exposed",),
                ("portRow.pane.inspectorBridgeRef.set_selected_port_exposed",),
            ),
        }

        for relative_path, (absent_snippets, present_snippets) in expectations.items():
            qml_path = _REPO_ROOT / relative_path
            qml_text = qml_path.read_text(encoding="utf-8")

            for snippet in absent_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="absent"):
                    self.assertNotIn(snippet, qml_text)

            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="present"):
                    self.assertIn(snippet, qml_text)


class ShellWorkspaceBridgeQmlBoundaryTests(unittest.TestCase):
    def test_workspace_run_title_and_console_qml_routes_owned_concerns_through_shell_workspace_bridge(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.project_display_name",
                ),
                (
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.project_display_name",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.request_run_workflow",
                    "mainWindowRef.request_toggle_run_pause",
                    "mainWindowRef.request_stop_workflow",
                    "mainWindowRef.show_workflow_settings_dialog",
                    "mainWindowRef.set_script_editor_panel_visible",
                ),
                (
                    "property var viewBridgeRef",
                    "property var scriptEditorBridgeRef",
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.request_run_workflow",
                    "root.workspaceBridgeRef.request_toggle_run_pause",
                    "root.workspaceBridgeRef.request_stop_workflow",
                    "root.workspaceBridgeRef.show_workflow_settings_dialog",
                    "root.workspaceBridgeRef.set_script_editor_panel_visible",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml": (
                (
                    "mainWindowRef.graphics_tab_strip_density",
                    "mainWindowRef.active_scope_breadcrumb_items",
                    "mainWindowRef.active_view_items",
                    "mainWindowRef.active_workspace_id",
                    "mainWindowRef.request_open_scope_breadcrumb",
                    "mainWindowRef.request_switch_view",
                    "mainWindowRef.request_move_view_tab",
                    "mainWindowRef.request_rename_view",
                    "mainWindowRef.request_close_view",
                    "mainWindowRef.request_create_view",
                    "mainWindowRef.request_move_workspace_tab",
                    "mainWindowRef.request_rename_workspace_by_id",
                    "mainWindowRef.request_close_workspace_by_id",
                    "mainWindowRef.request_create_workspace",
                    "property var workspaceTabsBridgeRef",
                    "property var consoleBridgeRef",
                    "workspaceTabsBridgeRef.tabs",
                    "workspaceTabsBridgeRef.activate_workspace",
                    "consoleBridgeRef.error_count_value",
                    "consoleBridgeRef.warning_count_value",
                    "consoleBridgeRef.clear_all",
                    "consoleBridgeRef.output_text",
                    "consoleBridgeRef.errors_text",
                    "consoleBridgeRef.warnings_text",
                    "property var mainWindowRef",
                    "property var sceneBridgeRef",
                    "property var viewBridgeRef",
                    "property var graphCanvasBridgeRef",
                    "canvasBridge: root.graphCanvasBridgeRef",
                ),
                (
                    "property var graphCanvasStateBridgeRef",
                    "property var graphCanvasCommandBridgeRef",
                    "property var overlayHostItem",
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.graphics_tab_strip_density",
                    "root.workspaceBridgeRef.active_scope_breadcrumb_items",
                    "root.workspaceBridgeRef.active_view_items",
                    "root.workspaceBridgeRef.active_workspace_id",
                    "root.workspaceBridgeRef.request_open_scope_breadcrumb",
                    "root.workspaceBridgeRef.request_switch_view",
                    "root.workspaceBridgeRef.request_move_view_tab",
                    "root.workspaceBridgeRef.request_rename_view",
                    "root.workspaceBridgeRef.request_close_view",
                    "root.workspaceBridgeRef.request_create_view",
                    "root.workspaceBridgeRef.request_move_workspace_tab",
                    "root.workspaceBridgeRef.request_rename_workspace_by_id",
                    "root.workspaceBridgeRef.request_close_workspace_by_id",
                    "root.workspaceBridgeRef.request_create_workspace",
                    "root.workspaceBridgeRef.workspace_tabs",
                    "root.workspaceBridgeRef.activate_workspace",
                    "root.workspaceBridgeRef.error_count_value",
                    "root.workspaceBridgeRef.warning_count_value",
                    "root.workspaceBridgeRef.clear_all",
                    "root.workspaceBridgeRef.output_text",
                    "root.workspaceBridgeRef.errors_text",
                    "root.workspaceBridgeRef.warnings_text",
                    "canvasStateBridge: root.graphCanvasStateBridgeRef",
                    "canvasCommandBridge: root.graphCanvasCommandBridgeRef",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.set_script_editor_panel_visible(false)",
                ),
                (
                    "property var scriptEditorBridgeRef",
                    "property var scriptHighlighterBridgeRef",
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.set_script_editor_panel_visible(false)",
                ),
            ),
        }

        for relative_path, (absent_snippets, present_snippets) in expectations.items():
            qml_path = _REPO_ROOT / relative_path
            qml_text = qml_path.read_text(encoding="utf-8")

            for snippet in absent_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="absent"):
                    self.assertNotIn(snippet, qml_text)

            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="present"):
                    self.assertIn(snippet, qml_text)

    def test_main_shell_keeps_only_the_remaining_live_shell_plumbing_assignments(self) -> None:
        qml_path = _REPO_ROOT / "ea_node_editor/ui_qml/MainShell.qml"
        qml_text = qml_path.read_text(encoding="utf-8")

        absent_snippets = (
            "typeof graphCanvasBridge",
            "typeof mainWindow",
            "typeof sceneBridge",
            "typeof viewBridge",
            "workspaceTabsBridgeRef: workspaceTabsBridge",
            "consoleBridgeRef: consoleBridge",
            "mainWindowRef: mainWindow",
            "sceneBridgeRef: root.sceneBridgeRef",
            "viewBridgeRef: root.viewBridgeRef",
            "viewBridgeRef: viewBridge",
            "readonly property var canvasShellBridgeRef",
            "readonly property var canvasSceneBridgeRef",
        )
        present_snippets = (
            "readonly property var canvasBridgeRef: graphCanvasBridge",
            "readonly property var canvasStateBridgeRef: graphCanvasStateBridge",
            "readonly property var canvasCommandBridgeRef: graphCanvasCommandBridge",
            "readonly property var canvasViewBridgeRef: root.canvasStateBridgeRef",
            "WorkspaceCenterPane {",
            "graphCanvasStateBridgeRef: root.canvasStateBridgeRef",
            "graphCanvasCommandBridgeRef: root.canvasCommandBridgeRef",
            "overlayHostItem: root",
            "viewBridgeRef: root.canvasViewBridgeRef",
            "ShellStatusStrip {",
            "canvasBridgeRef: root.canvasBridgeRef",
            "scriptEditorBridgeRef: scriptEditorBridge",
            "scriptHighlighterBridgeRef: scriptHighlighterBridge",
        )

        for snippet in absent_snippets:
            with self.subTest(snippet=snippet, expectation="absent"):
                self.assertNotIn(snippet, qml_text)

        for snippet in present_snippets:
            with self.subTest(snippet=snippet, expectation="present"):
                self.assertIn(snippet, qml_text)


class ShellStatusStripQmlBoundaryTests(unittest.TestCase):
    def test_status_strip_routes_graphics_quick_toggle_through_graph_canvas_bridge(self) -> None:
        qml_path = _REPO_ROOT / "ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml"
        qml_text = qml_path.read_text(encoding="utf-8")

        absent_snippets = (
            "property var mainWindowRef",
            "mainWindowRef.graphics_performance_mode",
            "mainWindowRef.set_graphics_performance_mode",
        )
        present_snippets = (
            'objectName: "shellStatusStrip"',
            "property var canvasBridgeRef",
            "readonly property string graphicsPerformanceMode",
            "readonly property string graphicsPerformanceModeLabel",
            'objectName: "shellStatusStripGraphicsModeSummary"',
            'objectName: "shellStatusStripFullFidelityButton"',
            'objectName: "shellStatusStripMaxPerformanceButton"',
            "tooltipText: root.fullFidelityCopy",
            "tooltipText: root.maxPerformanceCopy",
            'root.canvasBridgeRef.set_graphics_performance_mode("full_fidelity")',
            'root.canvasBridgeRef.set_graphics_performance_mode("max_performance")',
        )

        for snippet in absent_snippets:
            with self.subTest(snippet=snippet, expectation="absent"):
                self.assertNotIn(snippet, qml_text)

        for snippet in present_snippets:
            with self.subTest(snippet=snippet, expectation="present"):
                self.assertIn(snippet, qml_text)


class GraphCanvasQmlBoundaryTests(unittest.TestCase):
    def test_graph_canvas_routes_owned_concerns_through_bridge_first_refs(self) -> None:
        qml_path = _REPO_ROOT / "ea_node_editor/ui_qml/components/GraphCanvas.qml"
        qml_text = qml_path.read_text(encoding="utf-8")

        absent_snippets = (
            "property var canvasBridge: null",
            "readonly property var canvasBridgeRef",
            "mainWindowBridge.graphics_minimap_expanded",
            "mainWindowBridge.graphics_show_grid",
            "mainWindowBridge.graphics_show_minimap",
            "mainWindowBridge.graphics_node_shadow",
            "mainWindowBridge.graphics_shadow_strength",
            "mainWindowBridge.graphics_shadow_softness",
            "mainWindowBridge.graphics_shadow_offset",
            "mainWindowBridge.snap_to_grid_enabled",
            "mainWindowBridge.snap_grid_size",
            "mainWindowBridge.request_open_subnode_scope",
            "mainWindowBridge.browse_node_property_path",
            "mainWindowBridge.request_drop_node_from_library",
            "mainWindowBridge.request_connect_ports",
            "mainWindowBridge.request_open_connection_quick_insert",
            "sceneBridge.nodes_model",
            "sceneBridge.selected_node_lookup",
            "sceneBridge.select_node",
            "sceneBridge.set_node_property",
            "sceneBridge.are_port_kinds_compatible",
            "sceneBridge.are_data_types_compatible",
            "sceneBridge.move_nodes_by_delta",
            "sceneBridge.move_node",
            "sceneBridge.resize_node",
            "viewBridge.adjust_zoom",
            "viewBridge.pan_by",
            "viewBridge.set_viewport_size",
            "viewBridge.zoom_value",
            "viewBridge.center_x",
            "viewBridge.center_y",
            "property var hoveredPort: null",
            "property var pendingConnectionPort: null",
            "property var wireDragState: null",
            "property bool edgeContextVisible: false",
            "property bool interactionActive: false",
            "readonly property var _canvasCommandBridgeRef",
            "readonly property var _canvasShellBridgeRef",
            "readonly property var _canvasSceneBridgeRef",
            "readonly property var _canvasViewBridgeRef",
            "readonly property var _canvasShellCompatRef",
            "readonly property var _canvasSceneCompatRef",
            "readonly property var _canvasViewCompatRef",
        )
        present_snippets = (
            "property var canvasStateBridge: null",
            "property var canvasCommandBridge: null",
            "property var mainWindowBridge: root.canvasCommandBridgeRef",
            "property var sceneBridge: root.canvasStateBridgeRef",
            "property var viewBridge: root.canvasStateBridgeRef",
            "readonly property var canvasStateBridgeRef",
            "readonly property var canvasCommandBridgeRef",
            "readonly property var _canvasStateBridgeRef",
            "readonly property var _canvasSceneStateBridgeRef",
            "readonly property var _canvasViewStateBridgeRef",
            "readonly property var _canvasShellCommandBridgeRef",
            "readonly property var _canvasSceneCommandBridgeRef",
            "readonly property var _canvasViewCommandBridgeRef",
            "root._canvasStateBridgeRef.graphics_show_grid",
            "root._canvasSceneStateBridgeRef.nodes_model",
            "bridge.selected_node_lookup",
            "GraphCanvasComponents.GraphCanvasInteractionState {",
            "property alias hoveredPort: interactionState.hoveredPort",
            "property alias pendingConnectionPort: interactionState.pendingConnectionPort",
            "property alias interactionActive: interactionState.interactionActive",
            "interactionState.updateLibraryDropPreview(screenX, screenY, payload);",
            "interactionState.beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY);",
            "var bridge = root._canvasShellCommandBridgeRef",
            "var bridge = root._canvasSceneCommandBridgeRef",
            "var view = root._canvasViewStateBridgeRef",
            "scale: root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.zoom_value : 1.0",
            "viewBridge: root._canvasViewStateBridgeRef",
            "sceneBridge: root._canvasSceneStateBridgeRef",
            "shellCommandBridge: root._canvasShellCommandBridgeRef",
            "sceneCommandBridge: root._canvasSceneCommandBridgeRef",
            "sceneStateBridge: root._canvasSceneStateBridgeRef",
            "viewStateBridge: root._canvasViewStateBridgeRef",
            "viewCommandBridge: root._canvasViewCommandBridgeRef",
            "target: root._canvasSceneStateBridgeRef",
            "target: root._canvasViewStateBridgeRef",
        )

        for snippet in absent_snippets:
            with self.subTest(snippet=snippet, expectation="absent"):
                self.assertNotIn(snippet, qml_text)

        for snippet in present_snippets:
            with self.subTest(snippet=snippet, expectation="present"):
                self.assertIn(snippet, qml_text)

    def test_graph_canvas_interaction_state_helper_owns_extracted_canvas_state(self) -> None:
        helper_path = _REPO_ROOT / "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml"
        helper_text = helper_path.read_text(encoding="utf-8")

        present_snippets = (
            "property var pendingConnectionPort: null",
            "property var wireDragState: null",
            "property bool edgeContextVisible: false",
            "property bool interactionActive: false",
            "property var interactionIdleTimer: null",
            "function updateLibraryDropPreview(screenX, screenY, payload) {",
            "function finishPortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) {",
            "function _openNodeContext(nodeId, x, y) {",
            "function resetSceneBridgeState() {",
        )

        for snippet in present_snippets:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, helper_text)

    def test_overlay_host_item_plumbing_remains_live_for_canvas_overlay_paths(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/MainShell.qml": (
                "WorkspaceCenterPane {",
                "overlayHostItem: root",
            ),
            "ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml": (
                "property var overlayHostItem",
                "overlayHostItem: root.overlayHostItem",
            ),
            "ea_node_editor/ui_qml/components/GraphCanvas.qml": (
                "property var overlayHostItem: null",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml": (
                "var overlayHost = root.canvasItem.overlayHostItem || root.canvasItem;",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml": (
                "root.canvasItem.overlayHostItem ? root.canvasItem.overlayHostItem : root.canvasItem",
            ),
        }

        for relative_path, present_snippets in expectations.items():
            qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet):
                    self.assertIn(snippet, qml_text)


__all__ = [
    "ShellLibraryBridgeQmlBoundaryTests",
    "ShellInspectorBridgeQmlBoundaryTests",
    "ShellWorkspaceBridgeQmlBoundaryTests",
    "GraphCanvasQmlBoundaryTests",
]
