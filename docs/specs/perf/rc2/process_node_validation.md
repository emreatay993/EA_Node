# RC2 Process Node Validation

## Scope

- Node: `io.process_run`
- Behavior: success path, timeout handling, non-zero return handling, active cancellation on `stop_run`.

## Automated Evidence

- `tests/test_process_run_node_rc2.py::test_process_run_node_success_path`
- `tests/test_process_run_node_rc2.py::test_process_run_node_nonzero_and_timeout`
- `tests/test_process_run_node_rc2.py::test_stop_run_cancels_active_process_node`

## Results

- Success command execution: PASS (stdout captured, exit code propagated).
- Non-zero with `fail_on_nonzero=True`: PASS (raises runtime error).
- Timeout handling: PASS (raises timeout error and terminates process).
- Worker `stop_run` cancellation of active subprocess: PASS (`run_stopped` emitted, no `run_failed`).

