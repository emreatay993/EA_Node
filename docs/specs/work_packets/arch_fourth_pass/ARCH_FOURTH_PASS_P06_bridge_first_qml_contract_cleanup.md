# ARCH_FOURTH_PASS P06: Bridge-First QML Contract Cleanup

## Objective
- Finish packet-owned QML migration onto focused bridge contracts, remove packet-owned reliance on raw compatibility fallbacks, and move shared helper logic to neutral support modules below both `ui` and `ui_qml`.

## Preconditions
- `P05` is marked `PASS` in [ARCH_FOURTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_STATUS.md).
- `P03` remains `PASS`.

## Execution Dependencies
- `P05`

## Target Subsystems
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- shared helper modules below `ui` and `ui_qml`

## Conservative Write Scope
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/*.py`
- `ea_node_editor/ui/shell/window_library_inspector.py`
- `ea_node_editor/ui/shell/controllers/workspace_view_nav_ops.py`
- `ea_node_editor/ui/**/*.py`
- `tests/test_main_window_shell.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/arch_fourth_pass/P06_bridge_first_qml_contract_cleanup_WRAPUP.md`

## Required Behavior
- Move packet-owned QML roots and packet-owned canvas flows onto focused bridge contracts instead of `mainWindow`, `sceneBridge`, and `viewBridge` fallbacks.
- Keep raw compatibility exports only where a non-packet-owned or explicitly deferred consumer still requires them.
- Extract shared payload/geometry/presentation helpers into a neutral support module rather than leaving them in `ui` or `ui_qml` package internals on the wrong side of the seam.
- Preserve public QML object names and bridge contracts relied on by tests unless a packet-owned replacement path is fully wired and verified.

## Non-Goals
- No broad shell presenter/state ownership refactor; `P05` owns that.
- No verification/docs manifest consolidation yet; `P07` owns that.
- No packet-owned passive-media feature work beyond contract cleanup required by the bridge-first migration.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_graph_scene_bridge_bind_regression tests.test_graph_surface_input_contract tests.test_passive_graph_surface_host -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_fourth_pass/P06_bridge_first_qml_contract_cleanup_WRAPUP.md`

## Acceptance Criteria
- Packet-owned QML roots no longer require raw compatibility fallback paths for their primary shell/canvas behavior.
- `ui` and `ui_qml` no longer reach through each other for packet-owned shared helper logic.
- Packet verification passes through the project venv.

## Handoff Notes
- `P07` will consolidate verification metadata and tests; keep any new bridge contracts/documentation clear enough to anchor there.
- If some compatibility exports remain for deferred consumers, record them explicitly in the wrap-up rather than leaving them implicit.
