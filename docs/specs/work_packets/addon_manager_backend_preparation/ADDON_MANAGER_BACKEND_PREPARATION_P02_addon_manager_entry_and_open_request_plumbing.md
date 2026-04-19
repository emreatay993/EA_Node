# ADDON_MANAGER_BACKEND_PREPARATION P02: Add-On Manager Entry And Open-Request Plumbing

## Objective

- Add the menubar `Add-On Manager` entry and the shell-level open-manager request plumbing so later packets can route users from locked nodes into the manager without first building the full Variant 4 surface.

## Preconditions

- `P00` is marked `PASS`.
- No later `ADDON_MANAGER_BACKEND_PREPARATION` packet is in progress.

## Execution Dependencies

- `P00`

## Target Subsystems

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_basics_and_search.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `docs/specs/work_packets/addon_manager_backend_preparation/P02_addon_manager_entry_and_open_request_plumbing_WRAPUP.md`

## Required Behavior

- Add a top-level `Add-On Manager` action in the existing menubar surface with stable action naming and menu placement.
- Introduce a shell-side open-manager request path that can optionally focus a specific add-on id later.
- Preserve current shell startup and workflow-settings behavior; this packet adds a new entry point and open state seam, not the final manager UI.
- Make the new entry point available to later graph-node affordances without requiring direct graph-to-dialog coupling.

## Non-Goals

- No final Variant 4 layout yet; that belongs to `P07`.
- No locked-node visuals or graph interaction blocking yet; that belongs to `P04`.
- No plugin state or add-on catalog contract work beyond consuming the stable interface from `P01`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/addon_manager_backend_preparation/P02_addon_manager_entry_and_open_request_plumbing_WRAPUP.md`

## Acceptance Criteria

- The shell exposes a stable `Add-On Manager` entry point from the menubar.
- Shell code can accept and preserve an open-manager request, including a later add-on focus id, without building the final surface yet.
- The inherited main-window shell regressions pass.

## Handoff Notes

- `P04` and `P07` rely on this packet's open-manager request seam. Keep the request interface generic so graph affordances and final UI can share it.
