# PROJECT_MANAGED_FILES P06: Source Import Defaults

## Objective
- Add the app-level default for source-file handling and the managed-copy import service used by current image/PDF/source browse flows so importing can either stage a managed copy or keep an external link by policy.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`

## Target Subsystems
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/settings.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_app_preferences_import_defaults.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_pdf_preview_provider.py`

## Conservative Write Scope
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/settings.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_app_preferences_import_defaults.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_pdf_preview_provider.py`
- `docs/specs/work_packets/project_managed_files/P06_source_import_defaults_WRAPUP.md`

## Required Behavior
- Add an app preference for source-file handling with `managed_copy` as the default and `external_link` as the alternate mode.
- Make current source browse/import flows follow that default mode for relevant image/PDF/source-file nodes.
- In `managed_copy` mode, stage the imported file through the artifact service and persist a project-managed ref string instead of a raw copied path.
- In `external_link` mode, preserve the raw absolute path or local file URL behavior.
- Keep source-path properties string-based and backward compatible with existing external documents.
- Re-importing a managed source for the same node/path should replace the current staged managed copy rather than accumulate duplicates.
- Add narrow regression coverage for the new preference normalization and the browse/import behavior it controls.

## Non-Goals
- No node-level convert/repair actions yet. `P07` owns user-facing conversions after import.
- No project-files dialog or project-wide summary UX yet.
- No heavy-output runtime protocol or stored-output UI changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_app_preferences_import_defaults.py tests/test_graph_surface_input_contract.py tests/test_pdf_preview_provider.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_app_preferences_import_defaults.py --ignore=venv -q`

## Expected Artifacts
- `tests/test_app_preferences_import_defaults.py`
- `docs/specs/work_packets/project_managed_files/P06_source_import_defaults_WRAPUP.md`

## Acceptance Criteria
- A persisted app preference controls whether new source imports default to managed copy or external link.
- Managed-copy imports stage into the project artifact service and persist project-managed refs.
- External-link mode preserves the current raw-path behavior.
- Re-importing the same managed source replaces the current managed copy for that logical slot.

## Handoff Notes
- `P07` inherits the import behavior here when it adds convert/repair actions.
- Record the exact preference key and default value in the wrap-up so later UI packets use the same terminology.
