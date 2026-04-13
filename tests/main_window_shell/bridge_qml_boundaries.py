from __future__ import annotations

import unittest

import pytest

from tests.main_window_shell.bridge_contracts import _REPO_ROOT

pytestmark = pytest.mark.xdist_group("p03_bridge_contracts")


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

    def test_nested_category_qml_library_pane_uses_flattened_row_metadata(self) -> None:
        qml_path = _REPO_ROOT / "ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml"
        qml_text = qml_path.read_text(encoding="utf-8")

        present_snippets = (
            "ListView {",
            "function categoryKeyForRow(row) {",
            "return String(row.category_key || \"\")",
            "function depthForRow(row) {",
            "function ancestorsExpanded(ancestorCategoryKeys) {",
            "row.ancestor_category_keys || []",
            'objectName: "nodeLibraryRow"',
            "property string rowCategoryKey: root.categoryKeyForRow(modelData)",
            "property int rowDepth: root.depthForRow(modelData)",
            "property real rowIndent: root.rowIndentForRow(modelData)",
            "property bool hiddenByAncestors: root.isRowHiddenByAncestors(modelData)",
            "anchors.leftMargin: libraryRow.rowIndent",
            "root.isCategoryCollapsed(libraryRow.rowCategoryKey)",
            "root.setCategoryCollapsed(",
            "libraryRow.rowCategoryKey,",
            "Drag.active: !libraryRow.isCategory && mouseArea.drag.active",
            "root.graphCanvasRef.updateLibraryDropPreview",
            "root.graphCanvasRef.performLibraryDrop",
            "root.shellLibraryBridgeRef.request_add_node_from_library(modelData.type_id)",
        )
        absent_snippets = (
            "TreeView",
            "modelData.category",
            "split(\"",
            "split('",
            "collapsedCategories[normalizedCategory]",
        )

        for snippet in present_snippets:
            with self.subTest(snippet=snippet, expectation="present"):
                self.assertIn(snippet, qml_text)

        for snippet in absent_snippets:
            with self.subTest(snippet=snippet, expectation="absent"):
                self.assertNotIn(snippet, qml_text)


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
            "ea_node_editor/ui_qml/components/shell/InspectorColorField.qml": (
                ("mainWindowRef.pick_selected_node_property_color",),
                ("root.pane.inspectorBridgeRef.pick_selected_node_property_color",),
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
                    'objectName: "shellRunToolbarRunButton"',
                    'objectName: "shellRunToolbarPauseButton"',
                    'objectName: "shellRunToolbarStopButton"',
                    "enabled: root.workspaceBridgeRef.active_workspace_can_run",
                    "enabled: root.workspaceBridgeRef.active_workspace_can_pause",
                    "enabled: root.workspaceBridgeRef.active_workspace_can_stop",
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

    def test_shell_button_qml_mutes_disabled_visual_states(self) -> None:
        qml_path = _REPO_ROOT / "ea_node_editor/ui_qml/components/shell/ShellButton.qml"
        qml_text = qml_path.read_text(encoding="utf-8")

        present_snippets = (
            "readonly property color foregroundColor: !control.enabled",
            "Qt.alpha(control.themePalette.muted_fg, 0.55)",
            "readonly property color chromeBorderColor: !control.enabled",
            "readonly property color chromeFillColor: !control.enabled",
            "readonly property real contentOpacity: control.enabled ? 1.0 : 0.72",
            "property color iconColor: control.foregroundColor",
            "hoverEnabled: control.enabled",
            "ToolTip.visible: control.enabled && hovered && resolvedTooltipText.length > 0",
            "opacity: control.contentOpacity",
            "color: control.foregroundColor",
            "(control.enabled && control.down)",
            "(control.enabled && control.hovered)",
        )

        for snippet in present_snippets:
            with self.subTest(snippet=snippet):
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
            "readonly property var canvasBridgeRef: graphCanvasBridge",
            "canvasBridgeRef: root.canvasBridgeRef",
        )
        present_snippets = (
            "readonly property var canvasStateBridgeRef: graphCanvasStateBridge",
            "readonly property var canvasCommandBridgeRef: graphCanvasCommandBridge",
            "readonly property var canvasViewBridgeRef: graphCanvasViewBridge",
            "WorkspaceCenterPane {",
            "graphCanvasStateBridgeRef: root.canvasStateBridgeRef",
            "graphCanvasCommandBridgeRef: root.canvasCommandBridgeRef",
            "overlayHostItem: root",
            "viewBridgeRef: root.canvasViewBridgeRef",
            "ShellStatusStrip {",
            "canvasStateBridgeRef: root.canvasStateBridgeRef",
            "canvasCommandBridgeRef: root.canvasCommandBridgeRef",
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
    def test_status_strip_routes_graphics_quick_toggle_through_split_graph_canvas_bridges(self) -> None:
        qml_path = _REPO_ROOT / "ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml"
        qml_text = qml_path.read_text(encoding="utf-8")

        absent_snippets = (
            "property var mainWindowRef",
            "mainWindowRef.graphics_performance_mode",
            "mainWindowRef.set_graphics_performance_mode",
        )
        present_snippets = (
            'objectName: "shellStatusStrip"',
            "property var canvasStateBridgeRef",
            "property var canvasCommandBridgeRef",
            "readonly property string graphicsPerformanceMode",
            "readonly property string graphicsPerformanceModeLabel",
            'objectName: "shellStatusStripGraphicsModeSummary"',
            'objectName: "shellStatusStripFullFidelityButton"',
            'objectName: "shellStatusStripMaxPerformanceButton"',
            "tooltipText: root.fullFidelityCopy",
            "tooltipText: root.maxPerformanceCopy",
            'root.canvasCommandBridgeRef.set_graphics_performance_mode("full_fidelity")',
            'root.canvasCommandBridgeRef.set_graphics_performance_mode("max_performance")',
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
            "property var mainWindowBridge",
            "property var sceneBridge: root.canvasStateBridgeRef",
            "property var viewBridge: root.canvasStateBridgeRef",
            "readonly property var _canvasViewStateBridgeRef: root.canvasStateBridgeRef",
            "readonly property var _canvasViewCommandBridgeRef: root.canvasCommandBridgeRef",
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
            "readonly property var _canvasCompatBridgeRef",
        )
        present_snippets = (
            "property var canvasStateBridge: null",
            "property var canvasCommandBridge: null",
            'property var canvasViewBridge: typeof graphCanvasViewBridge !== "undefined"',
            "readonly property var canvasStateBridgeRef",
            "readonly property var canvasCommandBridgeRef",
            "readonly property var canvasViewBridgeRef",
            "readonly property var _canvasStateBridgeRef",
            "readonly property var _canvasSceneStateBridgeRef",
            "readonly property var _legacyCanvasViewBridgeRef",
            "readonly property var _canvasViewStateBridgeRef",
            "readonly property var _canvasShellCommandBridgeRef",
            "readonly property var _canvasSceneCommandBridgeRef",
            "readonly property var _canvasViewCommandBridgeRef",
            "readonly property var sceneBridge: root._canvasSceneStateBridgeRef",
            "readonly property var viewBridge: root._canvasViewStateBridgeRef",
            "root._canvasStateBridgeRef.graphics_show_grid",
            "root._canvasSceneStateBridgeRef.nodes_model",
            "GraphCanvasComponents.GraphCanvasInteractionState {",
            "GraphCanvasComponents.GraphCanvasSceneState {",
            "GraphCanvasComponents.GraphCanvasNodeSurfaceBridge {",
            "GraphCanvasComponents.GraphCanvasViewportController {",
            "GraphCanvasComponents.GraphCanvasSceneLifecycle {",
            "GraphCanvasComponents.GraphCanvasWorldLayer {",
            "readonly property var canvasViewportController: viewportController",
            "readonly property var canvasSceneLifecycle: sceneLifecycle",
            "property alias hoveredPort: interactionState.hoveredPort",
            "property alias pendingConnectionPort: interactionState.pendingConnectionPort",
            "property alias interactionActive: interactionState.interactionActive",
            "interactionState.updateLibraryDropPreview(screenX, screenY, payload);",
            "interactionState.beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY);",
            "viewportController.applyWheelZoom(eventObj);",
            "sceneLifecycle.requestEdgeRedraw();",
            "viewBridge: root._canvasViewStateBridgeRef",
            "sceneBridge: root._canvasSceneStateBridgeRef",
            "shellCommandBridge: root._canvasShellCommandBridgeRef",
            "sceneCommandBridge: root._canvasSceneCommandBridgeRef",
            "sceneStateBridge: root._canvasSceneStateBridgeRef",
            "viewStateBridge: root._canvasViewStateBridgeRef",
            "viewCommandBridge: root._canvasViewCommandBridgeRef",
        )

        for snippet in absent_snippets:
            with self.subTest(snippet=snippet, expectation="absent"):
                self.assertNotIn(snippet, qml_text)

        for snippet in present_snippets:
            with self.subTest(snippet=snippet, expectation="present"):
                self.assertIn(snippet, qml_text)

    def test_graph_typography_qml_contract_exposes_canvas_binding_and_shared_role_names(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml": (
                "readonly property int graphLabelPixelSize",
                "graphics_graph_label_pixel_size",
            ),
            "ea_node_editor/ui_qml/components/graph/GraphSharedTypography.qml": (
                'objectName: "graphSharedTypography"',
                "property int graphLabelPixelSize",
                "readonly property int nodeTitlePixelSize",
                "readonly property int portLabelPixelSize",
                "readonly property int elapsedFooterPixelSize",
                "readonly property int inlinePropertyPixelSize",
                "readonly property int badgePixelSize",
                "readonly property int edgeLabelPixelSize",
                "readonly property int edgePillPixelSize",
                "readonly property int execArrowPortPixelSize",
                "readonly property int nodeTitleFontWeight",
                "readonly property int portLabelFontWeight",
                "readonly property int inlinePropertyFontWeight",
                "readonly property int badgeFontWeight",
                "readonly property int edgeLabelFontWeight",
                "readonly property int edgePillFontWeight",
                "readonly property int execArrowPortFontWeight",
            ),
        }

        for relative_path, present_snippets in expectations.items():
            qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet):
                    self.assertIn(snippet, qml_text)

    def test_graph_node_icon_size_qml_contract_exposes_canvas_binding_and_shared_role_name(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml": (
                "readonly property var graphNodeIconPixelSizeOverride",
                "readonly property int nodeTitleIconPixelSize",
                "graphics_graph_node_icon_pixel_size_override",
                "graphics_node_title_icon_pixel_size",
            ),
            "ea_node_editor/ui_qml/components/graph/GraphSharedTypography.qml": (
                "property int graphNodeIconPixelSize",
                "readonly property int nodeTitleIconPixelSize",
            ),
        }

        for relative_path, present_snippets in expectations.items():
            qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet):
                    self.assertIn(snippet, qml_text)

    def test_persistent_node_elapsed_canvas_qml_properties_bind_only_to_state_bridge_execution_contract(
        self,
    ) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/GraphCanvas.qml": (
                "readonly property var runningNodeStartedAtMsLookup: rootBindings.runningNodeStartedAtMsLookup",
                "readonly property var nodeElapsedMsLookup: rootBindings.nodeElapsedMsLookup",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml": (
                "readonly property var runningNodeStartedAtMsLookup: root._canvasStateBridgeRef",
                "root._canvasStateBridgeRef.running_node_started_at_ms_lookup",
                "readonly property var nodeElapsedMsLookup: root._canvasStateBridgeRef",
                "root._canvasStateBridgeRef.node_elapsed_ms_lookup",
            ),
        }

        for relative_path, present_snippets in expectations.items():
            qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")

            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet):
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

    def test_graph_canvas_helper_components_hold_scene_surface_and_delegate_logic(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml": (
                "property var selectedEdgeIds: []",
                "function sceneNodePayload(nodeId) {",
                "function syncEdgePayload() {",
                'bridge && typeof bridge.selected_node_lookup !== "undefined"',
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml": (
                "GraphCanvasSurfaceInteractionHost {",
                "function requestOpenSubnodeScope(nodeId) {",
                "function commitNodeSurfaceProperties(nodeId, properties) {",
                "function browseNodePropertyPath(nodeId, key, currentPath) {",
                "function pickNodePropertyColor(nodeId, key, currentValue) {",
                "bridge.pick_node_property_color",
                "return hostInteraction.sceneSelectionBridge();",
                "hostInteraction.resetSurfaceInteractionState();",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasViewportController.qml": (
                "function applyWheelZoom(eventObj) {",
                "function requestViewStateRedraw() {",
                "function updateViewportSize() {",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneLifecycle.qml": (
                "function handleSceneMutation() {",
                "function resetCanvasSceneState() {",
                "target: root.sceneStateBridge",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml": (
                "GraphComponents.GraphNodeHost {",
                "property bool backdropInputOverlay: false",
                "canvasItem.requestEdgeRedraw",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasWorldLayer.qml": (
                "property bool backdropInputOverlay: false",
                "delegate: GraphCanvasNodeDelegate {",
                "scale: viewBridge ? viewBridge.zoom_value : 1.0",
            ),
        }

        for relative_path, present_snippets in expectations.items():
            qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet):
                    self.assertIn(snippet, qml_text)

    def test_graph_canvas_root_exposes_color_picker_helper_through_node_surface_bridge(self) -> None:
        qml_text = (_REPO_ROOT / "ea_node_editor/ui_qml/components/GraphCanvas.qml").read_text(encoding="utf-8")

        present_snippets = (
            "function pickNodePropertyColor(nodeId, key, currentValue) {",
            'GraphCanvasRootApi.invoke(nodeSurfaceBridge, "pickNodePropertyColor", [nodeId, key, currentValue], "")',
        )

        for snippet in present_snippets:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, qml_text)

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
