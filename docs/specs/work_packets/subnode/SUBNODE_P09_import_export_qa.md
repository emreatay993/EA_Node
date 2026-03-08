# SUBNODE P09: Import Export QA

## Objective
- Add `.eawf` import/export for custom workflows and close the roadmap with regression and traceability updates.

## Preconditions
- `P08` is marked `PASS` in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md).
- No later Subnode packet is in progress.

## Target Subsystems
- `ea_node_editor/custom_workflows/*`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `docs/specs/requirements/*`
- `tests/test_serializer.py`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_execution_worker.py`

## Required Behavior
- Add versioned `.eawf` import/export for one custom workflow snapshot definition.
- Keep `.eanp` node package behavior unchanged and separate from custom workflow assets.
- Finish traceability/requirements documentation updates for subnodes and custom workflows.
- Run the combined regression suite covering persistence, graph UX, shell flows, controller flows, and execution.
- Close any packet-level loose ends that block end-to-end authoring, execution, publish, import, and export flows.

## Non-Goals
- No new roadmap items beyond the agreed subnode feature set.
- No linked workflow instances.
- No replacement of the existing package/plugin format.

## Verification Commands
1. `venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_graph_track_b tests.test_main_window_shell tests.test_workspace_library_controller_unit tests.test_execution_worker -v`

## Acceptance Criteria
- Custom workflow definitions export to and import from `.eawf` without losing snapshot fidelity.
- Existing node package flows remain unchanged.
- The final regression command passes and traceability docs reference the completed subnode feature set.

## Handoff Notes
- This is the closing packet for the Subnode roadmap. Update the status ledger and any traceability references so the feature can be audited from docs alone.
