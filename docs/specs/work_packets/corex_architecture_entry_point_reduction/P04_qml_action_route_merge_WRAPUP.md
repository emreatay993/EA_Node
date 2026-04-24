# P04 QML Action Route Merge Wrap-Up

## Implementation Summary

- Packet: P04
- Branch Label: codex/corex-architecture-entry-point-reduction/p04-qml-action-route-merge
- Commit Owner: worker
- Commit SHA: eb04bdecbb2b4b9cabc9da74fcbafd1708adc08b
- Changed Files: docs/specs/work_packets/corex_architecture_entry_point_reduction/P04_qml_action_route_merge_WRAPUP.md, ea_node_editor/ui/shell/controllers/graph_action_controller.py, ea_node_editor/ui_qml/MainShell.qml, ea_node_editor/ui_qml/components/GraphCanvas.qml, ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml, ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml, ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml, ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml, ea_node_editor/ui_qml/graph_canvas_bridge.py, ea_node_editor/ui_qml/graph_canvas_command_bridge.py, tests/test_graph_action_contracts.py, tests/test_graph_scene_bridge_bind_regression.py, tests/test_main_window_shell.py
- Artifacts Produced: docs/specs/work_packets/corex_architecture_entry_point_reduction/P04_qml_action_route_merge_WRAPUP.md, ea_node_editor/ui/shell/controllers/graph_action_controller.py, ea_node_editor/ui_qml/MainShell.qml, ea_node_editor/ui_qml/components/GraphCanvas.qml, ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml, ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml, ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml, ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml, ea_node_editor/ui_qml/graph_canvas_bridge.py, ea_node_editor/ui_qml/graph_canvas_command_bridge.py, tests/test_graph_action_contracts.py, tests/test_graph_scene_bridge_bind_regression.py, tests/test_main_window_shell.py

P04 routes graph canvas context-menu and node-delegate graph verbs through `graphActionBridge.trigger_graph_action(actionId, payload)`. `graphActionBridge` is now passed through the shell, workspace center pane, canvas root bindings, and graph canvas context-menu/delegate access path.

Obsolete high-level `GraphCanvasCommandBridge` slots for context-menu and node-delegate actions were removed after static search showed app QML no longer references them. Low-level command bridge routes for selection, viewport, geometry, port drag, property commits, comment-peek dismissal, quick insert, and focus/interaction plumbing remain in place.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/passive_style_context_menus.py tests/main_window_shell/comment_backdrop_workflows.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q` (`247 passed, 4 warnings, 378 subtests passed`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_action_contracts.py --ignore=venv -q` (`29 passed, 20 warnings, 52 subtests passed`)
- Final Verification Verdict: PASS

## Manual Test Directives

- Open a graph with at least one flow edge, one passive node, one subnode, and one collapsed comment backdrop.
- Verify edge, node, and selection context-menu labels, visibility, destructive styling, close behavior, passive style actions, flow edge style actions, comment peek/exit, and wrap-into-frame behavior match the pre-P04 UI.
- Exercise node overlay actions for enter scope, delete, duplicate, and rename; rename should still activate the inline title editor rather than a modal dialog.

## Residual Risks

- No known residual implementation risks. The QML rename action now passes through `graphActionBridge` with an inline-title flag so the canonical action route sees the verb while preserving the established inline focus behavior.

## Ready for Integration

- Yes: P04 verification and review gate passed, the substantive packet commit is recorded, and the wrap-up artifact is ready for integration review.
