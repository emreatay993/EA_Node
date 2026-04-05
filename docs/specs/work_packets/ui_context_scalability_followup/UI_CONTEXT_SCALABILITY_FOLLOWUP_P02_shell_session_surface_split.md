# UI_CONTEXT_SCALABILITY_FOLLOWUP P02: Shell Session Surface Split

## Objective

- Split the remaining shell helper and project-session service umbrellas into curated support packages while keeping the legacy entry files import-compatible and capped as thin facades.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet is in progress.

## Execution Dependencies

- `P01`

## Target Subsystems

- `ea_node_editor/ui/shell/window_state_helpers.py`
- `ea_node_editor/ui/shell/window_state/*.py`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `ea_node_editor/ui/shell/controllers/project_session_services_support/*.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_files_dialog.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_contracts.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/window_state_helpers.py`
- `ea_node_editor/ui/shell/window_state/*.py`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `ea_node_editor/ui/shell/controllers/project_session_services_support/*.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_files_dialog.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_contracts.py`
- `docs/specs/work_packets/ui_context_scalability_followup/P02_shell_session_surface_split_WRAPUP.md`

## Required Behavior

- Split `window_state_helpers.py` into a curated `ea_node_editor/ui/shell/window_state/` package with these focused modules:
  - `context_properties.py`
  - `library_and_overlay_state.py`
  - `workspace_graph_actions.py`
  - `project_session_actions.py`
  - `run_and_style_state.py`
- Split `project_session_services.py` into a curated `ea_node_editor/ui/shell/controllers/project_session_services_support/` package with these focused modules:
  - `shared.py`
  - `project_files_service.py`
  - `session_lifecycle_service.py`
  - `document_io_service.py`
- Keep `window_state_helpers.py` as the stable facade entry surface and keep `project_session_services.py` as the stable facade entry surface.
- End the packet with `window_state_helpers.py` at or below `350` lines and `project_session_services.py` at or below `300` lines.
- Update inherited shell and project-session regression anchors in place when import paths or shared fixtures move.
- Preserve the shell packet invariants from `SHELL_PACKET.md`: lifecycle stays out of the helper package, and no packet-owned workflow logic moves back into `window.py`.

## Non-Goals

- No graph geometry or graph-scene mutation splits yet.
- No new shell behavior.
- No regression-suite packetization beyond updating inherited anchors that this packet invalidates.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/test_shell_project_session_controller.py tests/test_project_save_as_flow.py tests/test_project_files_dialog.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_contracts.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_project_session_controller.py tests/test_project_save_as_flow.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_followup/P02_shell_session_surface_split_WRAPUP.md`
- `ea_node_editor/ui/shell/window_state/context_properties.py`
- `ea_node_editor/ui/shell/controllers/project_session_services_support/project_files_service.py`

## Acceptance Criteria

- The legacy shell and project-session entry files remain stable import surfaces but are no longer omnibus implementation buckets.
- `window_state_helpers.py` is at or below `350` lines.
- `project_session_services.py` is at or below `300` lines.
- The inherited shell and project-session regression anchors pass.

## Handoff Notes

- `P05` is the first packet allowed to do the large bridge-contract regression-suite split on top of the slimmer shell helper surfaces from this packet.
