# EXECUTION_EDGE_PROGRESS_VISUALIZATION P03: Execution Edge Snapshot Metadata

## Objective
- Convert bridge-level progressed execution edge lookups into packet-owned edge-snapshot metadata and one-shot flash bookkeeping so the renderer can consume a stable control-edge contract instead of recomputing progress state ad hoc.

## Preconditions
- `P02` is marked `PASS` in [EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md](./EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md).
- No later `EXECUTION_EDGE_PROGRESS_VISUALIZATION` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- `tests/test_flow_edge_labels.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- `tests/test_flow_edge_labels.py`
- `docs/specs/work_packets/execution_edge_progress_visualization/P03_execution_edge_snapshot_metadata_WRAPUP.md`

## Required Behavior
- Thread `progressedExecutionEdgeLookup` and `nodeExecutionRevision` from the GraphCanvas root into `EdgeLayer` through `GraphCanvasRootLayers.qml`.
- Treat an edge as an execution edge only when its authored source port kind is `exec`, `completed`, or `failed`.
- Extend visible edge snapshots with packet-owned metadata fields named `executionProgressed`, `executionDimmed`, and `executionFlashProgress`.
- `executionProgressed` must reflect authored edge ids found in `progressedExecutionEdgeLookup`.
- `executionDimmed` must be `true` only for unprogressed execution edges that are not selected or previewed.
- `executionFlashProgress` must be QML-local and packet-owned: initialize a `240ms` one-shot flash only on the first unprogressed-to-progressed transition, do not restart it on redraws or stable already-progressed state, and keep it independent from Python-side timers or persistence.
- Keep selection and preview semantics intact: selected or previewed execution edges stay undimmed, but their snapshots still report execution progress and any active flash progress.
- Keep non-control edges unchanged: their packet-owned execution metadata must stay inert and must not alter their existing snapshot contracts.
- Add packet-owned regressions whose names include `execution_edge_progress_snapshot` so the verification commands below remain stable.

## Non-Goals
- No EdgeCanvas paint changes yet.
- No worker/runtime or bridge property renames.
- No requirement-doc or QA-matrix updates yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py -k execution_edge_progress_snapshot --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py -k execution_edge_progress_snapshot --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/execution_edge_progress_visualization/P03_execution_edge_snapshot_metadata_WRAPUP.md`

## Acceptance Criteria
- `EdgeLayer` consumes `progressedExecutionEdgeLookup` and `nodeExecutionRevision` from the packet-owned GraphCanvas contract.
- Visible edge snapshots expose stable `executionProgressed`, `executionDimmed`, and `executionFlashProgress` fields for authored control edges.
- Unprogressed control edges snapshot as dimmed, progressed control edges snapshot as undimmed, selected/previewed control edges remain undimmed, and non-control edges keep inert execution metadata.
- The packet-owned `execution_edge_progress_snapshot` regressions pass without any EdgeCanvas paint changes.

## Handoff Notes
- `P04` must consume `executionProgressed`, `executionDimmed`, and `executionFlashProgress` exactly as named here.
- Any later packet that needs to rename or reinterpret those snapshot fields must inherit and update the `tests/test_flow_edge_labels.py` regression anchor inside its own scope.
