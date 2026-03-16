# GRAPH_SURFACE_INPUT P09: Docs Traceability

## Objective
- Close the `GRAPH_SURFACE_INPUT` roadmap by updating TODO/docs/specs, recording the final QA matrix, and making the new input-routing rules discoverable for future node-surface work.

## Preconditions
- `P08` is marked `PASS` in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md).
- No later `GRAPH_SURFACE_INPUT` packet is in progress.

## Target Subsystems
- `TODO.md`
- `ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md`
- `docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md` (new if needed)

## Required Behavior
- Update `TODO.md` to remove or mark complete the open item about shared input-layer cleanup for interactive node surfaces.
- Update `ARCHITECTURE.md` to describe the locked host/surface input model:
  - under-surface host drag layer
  - `embeddedInteractiveRects`
  - `blocksHostInteraction`
  - shared graph-surface controls
- Update relevant QA/spec docs so the new pattern and acceptance matrix are represented in the canonical documentation.
- Add a final QA matrix artifact if it improves future handoff clarity.
- Run and record the final regression matrix across host, inline-control, media-surface, and shell coverage.
- If the exact aggregate shell wrapper still exits with environment-specific code `5`, record the fresh-process fallback explicitly and treat it as the approved gate only if the targeted matrix remains complete.

## Non-Goals
- No new runtime feature work.
- No new packet set beyond closing this one.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes -v`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_pdf_nodes -v`

## Acceptance Criteria
- The TODO item is closed.
- Architecture/spec/QA docs describe the locked future pattern clearly.
- The final QA matrix and status ledger make the packet set auditable end-to-end.

## Handoff Notes
- This is the final packet in the set. No later `GRAPH_SURFACE_INPUT` packet should be started.
