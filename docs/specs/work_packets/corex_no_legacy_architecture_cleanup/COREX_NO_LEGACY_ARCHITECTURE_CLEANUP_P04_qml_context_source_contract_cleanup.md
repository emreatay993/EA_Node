# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P04: QML Context Source Contract Cleanup

## Objective

- Shrink broad QML context globals and remove shell-window fallback discovery from bridge source contracts after graph-canvas and shell-action compatibility routes are gone.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only QML context/source bridge files needed for this packet

## Preconditions

- `P03` is marked `PASS`.
- Graph-canvas wrapper and shell graph-action facade cleanup have landed.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/context_bridges.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_support.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P04_qml_context_source_contract_cleanup_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/context_bridges.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_support.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P04_qml_context_source_contract_cleanup_WRAPUP.md`

## Required Behavior

- Replace presenter-or-host and ShellWindow fallback discovery in `shell_library_bridge`, `shell_workspace_bridge`, `shell_inspector_bridge`, `graph_canvas_state_bridge`, and `graph_canvas_command_bridge` with explicit injected source contracts.
- Shrink `shell_context_bootstrap.py` from a broad flat global-export layer toward one explicit shell/context bundle plus the genuinely top-level QML services still needed by current QML.
- Remove raw `typeof themeBridge`, `typeof addonManagerBridge`, `typeof helpBridge`, `typeof contentFullscreenBridge`, `typeof viewerSessionBridge`, and similar service lookups from graph-canvas descendants where explicit properties can be threaded from the shell/canvas owner.
- Keep feature-owned shell services available to QML, but make their ownership explicit instead of ambient.
- Update bridge-boundary tests so they assert explicit source injection and absence of fallback discovery.

## Non-Goals

- No GraphActionController route changes; those belong to P03.
- No viewer transport or host-service typed-state rewrite; that belongs to P12.
- No import-shim cleanup in package `__init__.py` files; that belongs to P13.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_support.py --ignore=venv -q`

## Review Gate

- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P04_qml_context_source_contract_cleanup_WRAPUP.md`

## Acceptance Criteria

- Packet-owned bridges no longer fall back to `ShellWindow` or dynamic presenter discovery.
- Packet-owned QML services are passed explicitly instead of discovered through broad raw globals.
- Shell/QML bridge tests prove the smaller context contract.

## Handoff Notes

- `P12` may still need typed viewer-specific bridge work; this packet should not try to solve viewer transport projection.
