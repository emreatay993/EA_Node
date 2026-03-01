Implement `RC2_P07_process_node.md`.

Constraints:
- Node type id must be `io.process_run`.
- Support inputs `command`, `args`, `stdin_text` and outputs `stdout`, `stderr`, `exit_code`, `exec_out`.
- `stop_run` while process node executes must terminate the subprocess and emit stop/failure state consistently.

Deliverables:
1. Process node implementation and bootstrap registration.
2. Worker cancellation integration for active subprocess.
3. New tests covering success/failure/timeout/stop.
4. Validation report artifact.

