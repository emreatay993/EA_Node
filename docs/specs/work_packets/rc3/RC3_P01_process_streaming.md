# RC3 P01: Process Streaming and Console Progress

## Objective
- Add incremental stdout/stderr streaming for `io.process_run` and surface in-app run progress updates without breaking existing completion/error flows.

## Non-Objectives
- No graph topology or scheduling algorithm redesign.
- No persistence schema version bump unless strictly required for backward-compatible metadata.

## Inputs
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/20_UI_UX.md`

## Allowed Files
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/nodes/builtins/integrations.py`
- `ea_node_editor/ui/main_window.py`
- `tests/test_process_run_node_rc2.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_client.py`
- `tests/test_main_window_shell.py`

## Do Not Touch
- `ea_node_editor/persistence/**`
- `docs/specs/requirements/**`

## Verification
1. `venv\Scripts\python -m unittest tests.test_process_run_node_rc2 tests.test_execution_worker tests.test_execution_client tests.test_main_window_shell -v`

## Output Artifacts
- `docs/specs/perf/rc3/process_streaming_validation.md`
- `docs/specs/perf/rc3/process_streaming_console.png`

## Merge Gate (Requirement IDs)
- `REQ-INT-006`
- `REQ-EXEC-002`
- `REQ-EXEC-007`
- `REQ-EXEC-008`
- `AC-REQ-QA-007-01`
