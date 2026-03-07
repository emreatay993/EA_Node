# RC3 Process Streaming Validation

- Packet: `RC3-P01`
- Date: `2026-03-01`
- Branch label: `rc3/p01-process-streaming`

## Scope

- Incremental stdout/stderr streaming for `io.process_run`.
- Event propagation through worker/client/main window console.
- Stop/cancel behavior regression coverage retained.
- Bounded capture path (queue + capped output buffers) for long-running/high-output commands.

## Verification Command

- `venv\Scripts\python -m unittest tests.test_process_run_node_rc2 tests.test_execution_worker tests.test_execution_client tests.test_main_window_shell -v`

## Test Summary

- Result: **PASS**
- Total: `26`
- Passed: `26`
- Failed: `0`
- Duration: `7.040s`

## Added/Updated Evidence Points

- `tests/test_process_run_node_rc2.py::test_process_run_node_streams_stdout_and_stderr_logs`
- `tests/test_execution_worker.py::test_run_workflow_streams_process_run_output_before_node_completion`
- `tests/test_execution_client.py::test_client_receives_streamed_process_output_events`
- `tests/test_main_window_shell.py::test_stream_log_events_are_scoped_to_active_run`

## Artifacts

- Console screenshot: `docs/specs/perf/rc3/process_streaming_console.png`
