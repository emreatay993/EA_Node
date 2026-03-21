# FLOWCHART_CARDINAL_PORTS P05: Regression Docs Traceability

## Objective
- Refresh the passive-flowchart reference evidence and update the requirements/traceability docs so the new cardinal neutral-port contract is documented and covered by a final focused regression gate.

## Preconditions
- `P00` is marked `PASS` in [FLOWCHART_CARDINAL_PORTS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md).
- No later `FLOWCHART_CARDINAL_PORTS` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`
- `P04`

## Target Subsystems
- `ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md`
- `tests/fixtures/passive_nodes/reference_flowchart.sfe`

## Conservative Write Scope
- `ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md`
- `tests/fixtures/passive_nodes/reference_flowchart.sfe`
- `docs/specs/work_packets/flowchart_cardinal_ports/P05_regression_docs_traceability_WRAPUP.md`

## Required Behavior
- Update architecture and requirements docs so the passive flowchart contract explicitly describes:
  - four stored cardinal flowchart ports (`top/right/bottom/left`)
  - `neutral` flowchart port direction
  - the `side` field on flowchart port payloads and the `origin_side` interaction payload used during neutral-port gestures
  - gesture-ordered source/target authoring for neutral flowchart edges
  - exact silhouette perimeter anchors for the four cardinal sides
  - removal of legacy decision-branch port identity in favor of edge labels/styling
  - non-flowchart fixed-direction behavior remaining unchanged
- Update QA/traceability references so the new flowchart contract and its focused regression commands are discoverable from the spec pack.
- Refresh `tests/fixtures/passive_nodes/reference_flowchart.sfe` and `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md` so the manual visual check matches the new four-handle flowchart behavior and the new `top/right/bottom/left` port keys.
- Run a final focused regression gate that covers passive flowchart contracts, scene routing, serializer/graph persistence, and passive runtime exclusion after the full packet set lands.

## Non-Goals
- No new runtime behavior.
- No additional packet set after this one.
- No repo-wide verification expansion beyond what is needed to prove the flowchart-cardinal-ports scope and docs alignment.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_graph_track_b tests.test_passive_node_contracts tests.test_passive_runtime_wiring tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_passive_flowchart_catalog tests.test_flowchart_visual_polish -v`
2. `./venv/Scripts/python.exe scripts/check_traceability.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/flowchart_cardinal_ports/P05_regression_docs_traceability_WRAPUP.md`

## Acceptance Criteria
- Requirements, architecture, QA, and traceability docs describe the new neutral cardinal flowchart port model accurately and without contradicting the preserved non-flowchart behavior.
- The passive reference workspace and manual checklist match the four-handle flowchart behavior and no longer reference legacy flowchart port keys.
- The final focused regression gate passes after the packet set is implemented.

## Handoff Notes
- Record the final regression command output summary in the wrap-up so future packet sets can reuse it instead of reconstructing a new proof slice.
- If any requirement text had to carve out a flowchart-neutral exception from a broader directionality rule, quote that exact wording in the wrap-up for future maintainers.
