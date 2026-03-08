# SUBNODE P07: Execution Compiler

## Objective
- Flatten nested subnode scopes into the worker's existing flat execution model immediately before execution.

## Preconditions
- `P06` is marked `PASS` in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md).
- No later Subnode packet is in progress.

## Target Subsystems
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/graph/hierarchy.py`
- `tests/test_execution_worker.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Add a dedicated execution compiler module that converts a nested workspace document into the worker's flat graph representation.
- Keep `core.subnode`, `core.subnode_input`, and `core.subnode_output` as compile-time-only constructs.
- Preserve inner real node ids so worker events still point to the original nested nodes.
- Preserve `data`, `exec`, `completed`, and `failed` flow semantics across any nesting depth.
- Keep UI/controllers unaware of compile details beyond existing execution entry points.

## Non-Goals
- No new graph editing UI.
- No library publishing/import/export behavior.
- No linked workflow instances.

## Verification Commands
1. `venv/Scripts/python.exe -m unittest tests.test_execution_worker tests.test_main_window_shell -v`

## Acceptance Criteria
- Nested data and execution flow runs successfully through the existing worker.
- Failure events can still be mapped back to the original nested node ids.
- The worker remains responsible only for execution, not for understanding subnode authoring UI.

## Handoff Notes
- `P08` and `P09` must treat published/imported custom workflows as snapshot authoring assets; execution should still depend on the compiler introduced here.
- Keep the compiler interface narrow so later packets can call it without duplicating flattening logic.
