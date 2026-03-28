# ARCHITECTURE_MAINTAINABILITY_REFACTOR P02: Bridge Source Contract Hardening

## Objective
- Replace presenter-or-host fallback across shell, workspace, library, inspector, and graph-canvas bridges with explicit injected source contracts so composition becomes the only wiring authority.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/bridge_contracts.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/bridge_contracts.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P02_bridge_source_contract_hardening_WRAPUP.md`

## Required Behavior
- Introduce explicit source contracts for every packet-owned bridge that still discovers a broader host when a presenter is absent.
- Make `composition.py` the only authority that wires bridge instances to their source contracts and exported context objects.
- Remove bridge-local fallback code that silently escalates from a narrow presenter contract back to the whole host.
- Update inherited shell runtime and bridge-boundary regression anchors in place when source ownership or object-wiring seams change.

## Non-Goals
- No further graph-canvas compatibility removal; `P01` already owns that.
- No `ShellWindow` host-method retirement yet; that belongs to `P03`.
- No project/session service decomposition yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/bridge_contracts.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P02_bridge_source_contract_hardening_WRAPUP.md`

## Acceptance Criteria
- Packet-owned bridges depend on explicit source contracts only.
- Composition is the single authority for bridge creation and context export wiring.
- The inherited shell bridge regression anchors pass without presenter-or-host fallback behavior.

## Handoff Notes
- `P03` should assume these bridge contracts are explicit and stable, then retire host-level pass-through APIs on top of them.
