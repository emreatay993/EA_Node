# GRAPH_SURFACE_INPUT P08: Pointer Regression Audit

## Objective
- Audit all graph-surface interactive regions for leftover top-overlay anti-patterns, add reusable pointer regression helpers, and lock the no-click-swallowing pattern for future surfaces.

## Preconditions
- `P07` is marked `PASS` in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md).
- No later `GRAPH_SURFACE_INPUT` packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/*`
- `ea_node_editor/ui_qml/components/graph/passive/*`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_inline.py`
- any new pointer-regression helper module or shell-harness helper required for stable coverage

## Required Behavior
- Audit graph-surface QML for leftover top-level click-swallowing patterns that bypass the new local interactive-region contract.
- Add reusable test helpers for pointer regression coverage so future packets can assert:
  - control clicks do not start host drag/open/context behavior
  - body clicks still do
  - modal whole-surface locks still work
- Where useful, add grep-backed coverage or audit commands that fail if private compatibility shims or banned top-overlay patterns reappear.
- Update affected tests to use the shared pointer-regression helpers instead of bespoke ad hoc probes where that reduces duplication.
- Record any unavoidable test-runner instability and the approved fallback strategy in the status ledger if the exact aggregate shell wrapper still exits with code `5`.

## Non-Goals
- No docs/TODO closure yet.
- No new feature work outside the audit/remediation scope.

## Verification Commands
1. `rg -n "hoverActionHitRect|graphNodeSurfaceHoverActionButton" ea_node_editor/ui_qml/components/graph ea_node_editor/ui_qml/components/graph/passive`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v`

## Acceptance Criteria
- No graph surface depends on the removed hover proxy compatibility layer.
- Pointer regression coverage exists for host body behavior, local control ownership, and modal whole-surface locks.
- Future interactive surfaces have a documented and tested pattern to follow.

## Handoff Notes
- `P09` closes the roadmap in docs, TODOs, and QA traceability.
