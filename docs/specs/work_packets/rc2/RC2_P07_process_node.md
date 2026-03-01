# RC2 P07: External Process Runner Node

## Objective
- Add `io.process_run` integration node with cancellation-aware execution semantics and robust runtime validation.

## Inputs
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`

## Allowed Files
- `ea_node_editor/nodes/builtins/integrations.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/execution/worker.py`
- `tests/test_process_run_node_rc2.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_client.py`

## Do Not Touch
- `ea_node_editor/ui/*` (unless minor messaging updates are required)

## Verification
1. `venv\Scripts\python -m unittest tests.test_process_run_node_rc2 tests.test_execution_worker tests.test_execution_client -v`

## Output Artifacts
- `docs/specs/perf/rc2/process_node_validation.md`

## Merge Gate
- Process node success/timeout/non-zero tests pass.
- Stop/cancel path can terminate active subprocess execution.

