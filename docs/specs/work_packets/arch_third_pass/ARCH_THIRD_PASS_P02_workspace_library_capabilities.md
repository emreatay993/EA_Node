# ARCH_THIRD_PASS P02: Workspace Library Capabilities

## Objective
- Split `workspace_library_controller.py` by business capability rather than verb buckets, extracting custom-workflow library management, search/focus flows, import/export, and edit-command orchestration into focused controllers or services without changing current QML-facing results or shell workflows.

## Preconditions
- `P00` and `P01` are marked `PASS` in [ARCH_THIRD_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_STATUS.md).
- No later `ARCH_THIRD_PASS` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- packet-owned controller modules under `ea_node_editor/ui/shell/controllers/`
- limited delegations in `ea_node_editor/ui/shell/window.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_window_library_inspector.py`
- `tests/test_workflow_settings_dialog.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- packet-owned controller modules under `ea_node_editor/ui/shell/controllers/`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_window_library_inspector.py`
- `tests/test_workflow_settings_dialog.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Split packet-owned workspace-library responsibilities by business capability rather than accumulating more helpers behind a single umbrella controller.
- Extract focused owners for custom-workflow library management, search/focus flows, import/export flows, and edit-command orchestration where those responsibilities are currently interleaved.
- Preserve current QML-facing results, emitted signals, and shell workflows for library, quick-insert, and workflow-settings interactions.
- Keep `window.py` delegations limited and explicit; new business behavior should not move back into the shell host.
- Preserve current custom-workflow import/export semantics and current workflow-settings dialog behavior.

## Non-Goals
- No bridge-first QML migration yet; `P03` owns packet-owned root-QML cleanup.
- No persistence schema changes or custom-workflow format changes.
- No user-visible changes to library search/filter results.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_workspace_library_controller_unit tests.test_window_library_inspector tests.test_workflow_settings_dialog tests.test_main_window_shell -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_workspace_library_controller_unit -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_third_pass/P02_workspace_library_capabilities_WRAPUP.md`

## Acceptance Criteria
- Packet-owned library responsibilities are owned by focused capability controllers/services instead of a single monolithic controller.
- Current shell and QML-facing library workflows behave the same from the user perspective.
- The targeted library/inspector/workflow-settings regressions pass.

## Handoff Notes
- `P03` migrates packet-owned root QML consumers onto focused bridges; keep capability outputs/contracts stable enough for that migration.
- Avoid pulling raw-bridge cleanup into this packet unless required for a minimal delegation fix.
