# SHELL_MOD P08: Workspace IO Extraction and Test Modularization

## Objective
- Extract custom workflow/package IO methods from `workspace_library_controller.py` and modularize oversized shell/controller test modules.

## Preconditions
- `P07` is marked `PASS` in [SHELL_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_io_ops.py` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/**` focused split modules (new)

## Required Behavior
- Extract custom workflow and node package import/export operations into helper module(s).
- Keep controller IO method names and user-visible messaging behavior stable.
- Split oversized shell/controller test modules into focused submodules while preserving test coverage and runnable entry modules.
- Ensure `tests.test_main_window_shell` and `tests.test_workspace_library_controller_unit` remain valid entrypoints for existing commands.

## Non-Goals
- No new runtime feature behavior.
- No requirements/doc rewrites outside status updates.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit tests.test_shell_run_controller tests.test_shell_project_session_controller tests.test_workspace_manager -v`

## Acceptance Criteria
- Controller IO logic is extracted and behavior-equivalent.
- Oversized tests are modularized but existing module entrypoints still execute full suites.
- Final regression gate passes.

## Handoff Notes
- Close the packet set by updating status ledger with final artifacts and residual risks.
