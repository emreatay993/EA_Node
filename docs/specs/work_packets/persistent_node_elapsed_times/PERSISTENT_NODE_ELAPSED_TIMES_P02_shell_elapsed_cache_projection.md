# PERSISTENT_NODE_ELAPSED_TIMES P02: Shell Elapsed Cache Projection

## Objective
- Extend shell run state and run handling with transient started-at tracking, per-workspace elapsed caching, and backward-compatible fallback timing behavior while keeping cached elapsed data independent from transient node chrome state.

## Preconditions
- `P01` is marked `PASS` in [PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md](./PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md).
- No later `PERSISTENT_NODE_ELAPSED_TIMES` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services_support/document_io_service.py`
- `tests/test_run_controller_unit.py`
- `tests/test_project_session_controller_unit.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services_support/document_io_service.py`
- `tests/test_run_controller_unit.py`
- `tests/test_project_session_controller_unit.py`
- `docs/specs/work_packets/persistent_node_elapsed_times/P02_shell_elapsed_cache_projection_WRAPUP.md`

## Required Behavior
- Extend `ShellRunState` with packet-owned transient running-node started-at state for the active run and a per-workspace cached elapsed-time lookup that survives run terminal events until execution-affecting invalidation occurs.
- Keep the cached elapsed lookup separate from `running_node_ids`, `completed_node_ids`, and authored execution-edge progress state so footer persistence does not keep completed border/highlight state alive after the run ends.
- Update shell helpers so `node_started` records a started-at value from `started_at_epoch_ms` when present and falls back to a local shell timestamp when the field is absent.
- Update shell helpers so `node_completed` prefers the worker-provided `elapsed_ms` when present, otherwise computes elapsed from the stored started-at fallback, and overwrites the cached elapsed value for that node only.
- Update `RunController.handle_execution_event()` so `run_started` clears transient running/completed/timing-live state without clearing cached elapsed data, while `run_completed`, `run_stopped`, and `run_failed` clear only transient live state and preserve the cache.
- Preserve stopped/failed partial-run semantics: only nodes that actually completed receive new cached elapsed values, and untouched cached nodes keep their prior values.
- Clear all cached elapsed timing data on project/session replacement paths such as `_install_project()` so timings never leak across projects before any history-based invalidation is introduced.
- Reuse the existing `node_execution_revision` invalidation path for timing-state changes rather than introducing a second packet-owned revision counter.
- Add packet-owned regression tests whose names include `persistent_node_elapsed_state` so the targeted verification commands below remain stable.

## Non-Goals
- No GraphCanvas bridge/property exposure yet.
- No history taxonomy split or edit-driven invalidation yet.
- No QML footer rendering or styling changes yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k persistent_node_elapsed_state --ignore=venv -q`
2. `.\venv\Scripts\python.exe -m pytest tests/test_project_session_controller_unit.py -k persistent_node_elapsed_state --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k persistent_node_elapsed_state --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/persistent_node_elapsed_times/P02_shell_elapsed_cache_projection_WRAPUP.md`

## Acceptance Criteria
- Shell run state records transient started-at values plus per-workspace cached elapsed values without coupling them to transient running/completed node chrome.
- `run_started`, `run_completed`, `run_stopped`, and `run_failed` follow the locked-default cache-preservation semantics.
- Project/session replacement clears cached elapsed timing data.
- Missing worker timing fields still produce correct shell timing behavior through the packet-owned fallback path.
- The packet-owned `persistent_node_elapsed_state` controller regressions pass.

## Handoff Notes
- `P03` treats the timing data shaped here as the authoritative bridge/footer source and should not rename the packet-owned lookup semantics casually.
- `P05` will invalidate the cache after execution-affecting edits, but it should preserve the storage split and project/session clearing established here.
