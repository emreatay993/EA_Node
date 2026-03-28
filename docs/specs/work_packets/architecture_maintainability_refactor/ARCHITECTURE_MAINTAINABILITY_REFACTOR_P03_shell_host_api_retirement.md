# ARCHITECTURE_MAINTAINABILITY_REFACTOR P03: Shell Host API Retirement

## Objective
- Cut `ShellWindow` down to lifecycle, top-level Qt ownership, and final signal wiring by moving application commands behind focused services or presenters and deleting host-level compatibility methods once callers are migrated.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/test_viewer_session_bridge.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/test_viewer_session_bridge.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P03_shell_host_api_retirement_WRAPUP.md`

## Required Behavior
- Move packet-owned non-lifecycle host behavior behind services, presenters, or focused bridge contracts.
- Delete pass-through host methods and compatibility aliases once their in-repo callers are migrated in this packet.
- Keep `ShellWindow` responsible for Qt lifecycle, window ownership, final signal wiring, and packet-owned top-level widget integration only.
- Update inherited shell/bootstrap/viewer regression anchors in place when host method names or attachment seams change.

## Non-Goals
- No project/session authority cleanup yet; that belongs to `P04`.
- No graph or runtime boundary work yet.
- No new user-facing shell features.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_contracts.py tests/test_viewer_session_bridge.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P03_shell_host_api_retirement_WRAPUP.md`

## Acceptance Criteria
- `ShellWindow` is no longer the broad packet-owned application-command surface.
- Packet-owned callers use focused services, presenters, or explicit bridge contracts instead of host pass-throughs.
- The inherited shell/bootstrap/viewer regression anchors pass after host API retirement.

## Handoff Notes
- `P04` should build project/session cleanup on top of a narrower host rather than reintroducing host-owned controller logic.
