# COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION P04: QML Action Route Merge

## Packet Metadata

- Packet: `P04`
- Title: `QML Action Route Merge`
- Execution Dependencies: `P03`
- Worker model: `gpt-5.5`
- Worker reasoning effort: `xhigh`

## Objective

- Route graph context menus and node delegate high-level actions through `graphActionBridge`, then remove obsolete high-level `GraphCanvasCommandBridge` slots once app QML no longer calls them.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, inherited action-contract tests, and only source files needed for QML action routing

## Preconditions

- `P03` is `PASS`.
- PyQt routes already dispatch through `GraphActionController`.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui_qml/graph_action_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/passive_style_context_menus.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_graph_scene_bridge_bind_regression.py`

## Conservative Write Scope

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P04_qml_action_route_merge_WRAPUP.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P04_qml_action_route_merge.md`
- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui_qml/graph_action_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/passive_style_context_menus.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_graph_scene_bridge_bind_regression.py`

## Required Behavior

- Pass `graphActionBridge` through the graph canvas root binding/component path where graph canvas QML needs it.
- Replace high-level action branches in `GraphCanvasContextMenus.qml` with calls to `graphActionBridge.trigger_graph_action(actionId, payload)`.
- Replace high-level action branches in `GraphCanvasNodeDelegate.qml` with calls to `graphActionBridge.trigger_graph_action(actionId, payload)` when the action represents a graph UI verb.
- Preserve direct canvas calls for low-level interaction plumbing: port drag, hover, inline property commit, geometry edits, selection rectangle, viewport movement, and focus handling.
- Remove high-level `GraphCanvasCommandBridge` slots only after static search proves app QML no longer references them. Keep low-level bridge methods that remain active in QML.
- Update inherited action-contract tests so QML action literals and bridge payload keys continue to match the canonical contract.
- Update QML/shell regressions that asserted old bridge ownership names or old high-level slot routes.

## Non-Goals

- Do not remove `GraphCanvasCommandBridge` entirely.
- Do not rewrite scene mutation history or graph model mutation paths.
- Do not change context-menu labels, visibility rules, destructive styling, or close behavior.
- Do not change comment peek, passive style, flow edge style, or subnode behavior beyond route ownership.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/passive_style_context_menus.py tests/main_window_shell/comment_backdrop_workflows.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_action_contracts.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P04_qml_action_route_merge_WRAPUP.md`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_graph_scene_bridge_bind_regression.py`

## Acceptance Criteria

- QML graph context menus and node delegate high-level graph actions dispatch through `graphActionBridge`.
- Existing context-menu visibility, labels, destructive flags, and close behavior remain unchanged.
- Obsolete high-level command bridge slots are removed only when unused by app QML and tests.
- Low-level canvas command bridge behavior remains intact.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- `P05` will publish docs and metrics for the new ownership path.
- If `P04` changes object names or bootstrap expectations asserted by `tests/test_main_window_shell.py`, the packet must update those assertions in scope.
- `ea_node_editor/ui_qml/components/GraphCanvas.qml` and `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml` are included only to pass `graphActionBridge` explicitly through the existing QML component path.
