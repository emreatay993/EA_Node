# EXECUTION_EDGE_PROGRESS_VISUALIZATION P01: Run State Edge Progress Projection

## Objective
- Add the handled-failure worker event plus run-scoped authored execution-edge progress projection on the worker/shell/controller path so later bridge and QML packets can consume stable authored edge ids without introducing persistence or a second execution-visualization signal path.

## Preconditions
- `P00` is marked `PASS` in [EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md](./EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md).
- No later `EXECUTION_EDGE_PROGRESS_VISUALIZATION` packet is in progress.

## Execution Dependencies
- `P00`

## Target Subsystems
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/worker_runner.py`
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `tests/test_execution_worker.py`
- `tests/test_run_controller_unit.py`

## Conservative Write Scope
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/worker_runner.py`
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `tests/test_execution_worker.py`
- `tests/test_run_controller_unit.py`
- `docs/specs/work_packets/execution_edge_progress_visualization/P01_run_state_edge_progress_projection_WRAPUP.md`

## Required Behavior
- Extend the worker protocol with a packet-owned `node_failed_handled` event carrying `run_id`, `workspace_id`, `node_id`, and `error`.
- Emit `node_failed_handled` when a node raises but execution continues through authored failure handlers, instead of treating that handled path as a silent shell-only concern.
- Extend `ShellRunState` with `progressed_execution_edge_ids: set[str]` and packet-owned run-scoped authored-edge lookup storage that can answer authored edge ids grouped by source node id and source port kind.
- Add shell/window helpers that clear packet-owned edge progress state, build a per-run authored-edge index from the run-start authored workspace snapshot, and mark authored edge ids as progressed for a workspace.
- Update `RunController` so `run_started` clears stale edge progress and reseeds the run-scoped authored-edge index, `node_completed` progresses authored `exec` and `completed` edges, `node_failed_handled` progresses authored `failed` edges, and terminal cleanup paths clear edge progress together with node execution state.
- Reuse the existing `node_execution_state_changed` and `node_execution_revision` invalidation path rather than introducing a second execution-edge signal or revision field.
- Keep the feature authored-edge-id based. Do not depend on flattened runtime edge ids because the runtime compiler strips edge ids during flattening.
- Keep the state run-scoped and ephemeral. Do not add `.sfe` persistence, session restore payloads, or project-file schema changes.
- Add packet-owned regressions whose names include `execution_edge_progress_projection` so the verification commands below remain stable.

## Non-Goals
- No GraphCanvas bridge property changes yet.
- No edge-layer snapshot metadata or paint changes yet.
- No QA-matrix or requirement-doc updates yet.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py -k execution_edge_progress_projection --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k execution_edge_progress_projection --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k execution_edge_progress_projection --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/execution_edge_progress_visualization/P01_run_state_edge_progress_projection_WRAPUP.md`

## Acceptance Criteria
- The worker emits `node_failed_handled` for handled failure paths, and that event round-trips through the typed worker protocol without regressing existing terminal failure behavior.
- `ShellRunState`, `ShellWindow`, and `RunController` maintain authored execution-edge progress by authored edge id, scoped to the active run workspace and cleared on the documented terminal/reset paths.
- `node_completed` progresses authored `exec` and `completed` edges, while `node_failed_handled` progresses authored `failed` edges.
- The packet-owned `execution_edge_progress_projection` regressions pass with no bridge, QML renderer, or docs changes.

## Handoff Notes
- `P02` consumes the packet-owned shell/controller contract and should treat `progressed_execution_edge_ids`, `mark_execution_edges_progressed`, and `node_failed_handled` as stable names.
- Any later packet that needs to rename or reshape those packet-owned seams must inherit and update the `tests/test_run_controller_unit.py` regression anchor inside its own scope.
