# P11 Shell QML Bridge Retirement Wrap-Up

## Implementation Summary

- Packet: `P11`
- Branch Label: `codex/architecture-refactor/p11-shell-qml-bridge-retirement`
- Commit Owner: `worker`
- Commit SHA: `de76878c80da80cafcbbf998d3fe18390ad5bd5c`
- Changed Files: `ea_node_editor/ui/perf/performance_harness.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml`, `ea_node_editor/ui_qml/graph_canvas_bridge.py`, `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`, `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`, `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `tests/graph_track_b/qml_preference_bindings.py`, `tests/main_window_shell/bridge_qml_boundaries.py`, `tests/main_window_shell/shell_runtime_contracts.py`, `tests/test_flow_edge_labels.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_main_window_shell.py`, `docs/specs/work_packets/architecture_refactor/P11_shell_qml_bridge_retirement_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/architecture_refactor/P11_shell_qml_bridge_retirement_WRAPUP.md`, `ea_node_editor/ui/perf/performance_harness.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml`, `ea_node_editor/ui_qml/graph_canvas_bridge.py`, `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`, `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`, `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `tests/graph_track_b/qml_preference_bindings.py`, `tests/main_window_shell/bridge_qml_boundaries.py`, `tests/main_window_shell/shell_runtime_contracts.py`, `tests/test_flow_edge_labels.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_main_window_shell.py`

Made `shell_context_bootstrap.py` the singular QML export authority for the shell canvas migration by removing legacy `graphCanvasBridge`, `consoleBridge`, and `workspaceTabsBridge` context exports and keeping only the bridge-first shell and graph bridge surfaces in the QML context.

Retired packet-owned `GraphCanvas.qml` fallback inputs by moving tracked consumers to `GraphCanvasStateBridge` and `GraphCanvasCommandBridge`, updating `MainShell.qml`, `ShellStatusStrip.qml`, the performance harness, and the packet-owned bridge-boundary tests to use the split bridge contract. The composite `GraphCanvasBridge` remains available as an internal compatibility wrapper for the Python host, but it now delegates state and command behavior to the split bridges instead of acting as the QML-facing authority.

Kept the shell host behavior stable by restoring packet-owned compatibility at the shell window edge where the migration exposed existing test contracts: custom workflow export now syncs a monkeypatched prompt callback into the package I/O controller before export, and `update_system_metrics()` once again treats omitted `fps` as `0.0` for callers that use the public window API.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/graph_track_b/qml_preference_bindings.py tests/test_graph_surface_input_contract.py tests/test_flow_edge_labels.py tests/test_main_window_shell.py tests/test_main_bootstrap.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_main_bootstrap.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Shell launch smoke: start the app from the repo `venv` in a normal desktop Qt session and open the main shell window. Expected result: the shell loads without missing-context QML errors, the workspace center renders, and the graph canvas appears with normal pan/zoom interaction.
2. Status strip performance-mode smoke: with a graph open, use the status strip performance-mode control to switch between the normal and max-performance options. Expected result: the selector updates immediately, the canvas remains interactive, and the graph surface simplifications engage only when the selected mode requires them instead of depending on any removed legacy bridge property.
3. Custom workflow round-trip smoke: export a simple custom workflow from the shell, then import it back into the same session. Expected result: the export completes without prompt-recursion failures, the import succeeds, and the reloaded workflow preserves the same nodes and connections.

## Residual Risks

`GraphCanvas.qml` still exposes read-only `sceneBridge` and `viewBridge` aliases for out-of-scope child QML consumers that have not yet been decomposed. That keeps the current shell behavior stable for P11, but P12 will need to retire those aliases carefully when it breaks up the scene and host hotspots.

The packet verified the bridge retirement with the owned offscreen regression suites only. An interactive desktop smoke run was not executed in this worktree, so user-observed rendering and status-strip behavior still rely on the automated shell/QML coverage plus the recommended manual checks above.

## Ready for Integration

- Yes: the bridge-first shell/QML contract is committed on the packet branch, the packet verification command and review gate both pass, and the remaining compatibility notes are limited to documented follow-on work for `P12`.
