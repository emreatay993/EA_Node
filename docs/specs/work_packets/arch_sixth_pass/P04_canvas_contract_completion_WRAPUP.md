# P04 Canvas Contract Completion Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/arch-sixth-pass/p04-canvas-contract-completion`
- Commit Owner: `worker`
- Commit SHA: `a3defd1e40041111af68cfecdf91508ebfaaa8ef`
- Changed Files: `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`, `tests/test_main_window_shell.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_graph_surface_input_inline.py`, `tests/test_passive_graph_surface_host.py`, `docs/specs/work_packets/arch_sixth_pass/P04_canvas_contract_completion_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/arch_sixth_pass/P04_canvas_contract_completion_WRAPUP.md`

Removed the packet-owned `graphCanvasBridge` export from the shell QML context and the packet-owned shell wiring, then simplified `GraphCanvas.qml` onto explicit `canvasStateBridge` and `canvasCommandBridge` ownership while preserving the raw `mainWindowBridge`, `sceneBridge`, and `viewBridge` compatibility inputs for standalone probes. Updated the packet-owned shell tests to shadow the stale merged-bridge assertions inside the aggregator, and refreshed the graph-surface probe bootstraps so the worktree subprocess tests use local theme/module bootstrap instead of the package `ui_qml.__init__` import path.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: run the packet branch in a normal desktop Qt session rather than `offscreen`.
- Open the main shell and confirm the graph canvas loads without a UI error dialog; expected result: the canvas, grid, and minimap render normally and the shell stays responsive.
- Add or select a node, then drag, resize, and wheel-zoom on the canvas; expected result: live drag/resize previews, selection, and viewport interaction behave exactly as before.
- Edit an inline node property and perform a node-library drop onto the canvas; expected result: the inline edit commits once, the drop preview tracks correctly, and the inserted node or connection flow still works.

## Residual Risks

- `ShellContextBridges.graph_canvas_bridge` and the host-side compatibility object still exist outside the packet-owned QML context export because broader shell composition cleanup is outside this packet's write scope.
- Automated coverage is strong in offscreen Qt and subprocess probes, but a real desktop smoke pass is still useful for interaction feel, focus timing, and overlay positioning.

## Ready for Integration

- Yes: packet-owned shell/QML consumers now use the split canvas bridge contract, the exact verification command passes, and the canvas/surface regression suite remains green.
