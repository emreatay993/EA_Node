# ARCH_THIRD_PASS P03: Bridge-First Shell And Canvas Roots

## Objective
- Migrate `MainShell.qml`, `WorkspaceCenterPane.qml`, and `GraphCanvas.qml` to focused bridge usage first, removing root-level fallback dependence on raw `mainWindow` / `sceneBridge` / `viewBridge` while keeping temporary compatibility exports only for packet-owned remaining consumers.

## Preconditions
- `P00`, `P01`, and `P02` are marked `PASS` in [ARCH_THIRD_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_STATUS.md).
- No later `ARCH_THIRD_PASS` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- bridge modules under `ea_node_editor/ui_qml/`
- `tests/test_main_window_shell.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- bridge modules under `ea_node_editor/ui_qml/`
- `tests/test_main_window_shell.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`

## Required Behavior
- Route packet-owned shell and canvas root consumers through focused bridges first instead of direct raw context-object reads/calls.
- Remove packet-owned root-level fallback dependence on raw `mainWindow`, `sceneBridge`, and `viewBridge` where explicit bridge contracts can own the same behavior.
- Keep temporary compatibility exports only for packet-owned remaining consumers that are not migrated yet, and trim packet-owned fallbacks that become unused inside this scope.
- Preserve the `GraphCanvas.qml` root integration contract and current shell/canvas workflows.
- Keep shell bootstrap/context registration aligned with the bridge-first ownership model introduced by this packet.

## Non-Goals
- No `GraphSceneBridge` internal extraction yet; `P04` owns that seam.
- No passive media-surface cleanup yet; `P05` owns that.
- No new user-visible shell or canvas features.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_graph_scene_bridge_bind_regression tests.test_graph_surface_input_contract -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_third_pass/P03_bridge_first_shell_canvas_WRAPUP.md`

## Acceptance Criteria
- Packet-owned root QML consumers no longer depend on raw shell/scene/view context objects for owned concerns.
- Temporary compatibility exports remain only where still required for non-packet-owned consumers.
- Main shell and graph-surface regressions pass with the bridge-first routing in place.

## Handoff Notes
- `P04` depends on the public bridge surface staying stable while internals move behind explicit scene services.
- Do not remove compatibility exports needed by non-packet-owned consumers that this packet does not migrate.
