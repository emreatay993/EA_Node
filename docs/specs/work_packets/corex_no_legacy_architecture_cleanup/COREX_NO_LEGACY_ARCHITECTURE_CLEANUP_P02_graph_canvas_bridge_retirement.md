# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P02: Graph Canvas Bridge Retirement

## Objective

- Retire the remaining monolithic `GraphCanvasBridge` wrapper, private graph-canvas bridge aliases, and low-level input-layer compatibility routes that survived the graph-action entry-point reduction.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only graph-canvas bridge/QML/test files needed for this packet

## Preconditions

- `P01` is marked `PASS`.
- `GraphActionController` and `GraphActionBridge` are the committed high-level graph action path.

## Execution Dependencies

- `P01`

## Target Subsystems

- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSurfaceInteractionHost.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostSceneAccess.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeFloatingToolbar.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceButton.qml`
- `tests/test_graph_action_contracts.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P02_graph_canvas_bridge_retirement_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSurfaceInteractionHost.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostSceneAccess.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeFloatingToolbar.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceButton.qml`
- `tests/test_graph_action_contracts.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P02_graph_canvas_bridge_retirement_WRAPUP.md`

## Required Behavior

- Delete `GraphCanvasBridge` as an active wrapper once all in-repo construction and tests use `GraphCanvasStateBridge`, `GraphCanvasCommandBridge`, `GraphActionBridge`, and `ViewportBridge` directly.
- Remove private QML compatibility aliases such as `_canvasShellCompatRef`, `_canvasSceneCompatRef`, `_canvasViewCompatRef`, `_canvasCompatBridgeRef`, `_legacyCanvasViewBridgeRef`, and redundant `*BridgeRef` translations where child components can consume canonical inputs.
- Route remaining input-layer `Delete`, scope navigation, Escape/comment-peek close, and related high-level command paths through `GraphActionBridge` or direct focused bridge methods; do not leave `shellCommandBridge` as a compatibility catch-all for packet-owned actions.
- Remove `typeof graphCanvasStateBridge` / `typeof graphCanvasViewBridge` raw-global lookups from graph-canvas child components by passing explicit properties.
- Update inherited QML bridge tests in place to assert the no-wrapper contract.

## Non-Goals

- No broad `shell_context_bootstrap.py` context shrink yet; that belongs to `P04`.
- No `ShellWindow` graph-action slot retirement yet; that belongs to `P03`.
- No comment floating popover implementation or mockup work.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_scene_bridge_bind_regression.py tests/test_main_window_shell.py tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/bridge_contracts_graph_canvas.py --ignore=venv -q`

## Review Gate

- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P02_graph_canvas_bridge_retirement_WRAPUP.md`

## Acceptance Criteria

- `graph_canvas_bridge.py` is deleted or reduced to a documented non-imported edge adapter only if an unavoidable in-repo caller is proven in the wrap-up.
- Packet-owned QML graph-canvas components no longer rely on private compatibility aliases or raw graph-canvas bridge globals.
- Input-layer high-level actions no longer bypass the graph-action path through compatibility command slots.

## Handoff Notes

- `P03` can assume high-level QML graph actions and graph-canvas child components no longer require legacy wrapper slots.
- `P04` inherits any remaining explicit QML context globals that are still feature-owned rather than compatibility-owned.
