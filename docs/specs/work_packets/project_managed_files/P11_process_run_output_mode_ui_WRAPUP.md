# P11 Process Run Output Mode UI Wrap-Up

## Implementation Summary

- Packet: `P11`
- Branch Label: `codex/project-managed-files/p11-process-run-output-mode-ui`
- Commit Owner: `worker`
- Commit SHA: `6c869a83cd374678d5e16314f1d776e91043f438`
- Changed Files: `ea_node_editor/nodes/builtins/integrations_process.py`, `ea_node_editor/ui/support/node_presentation.py`, `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`, `tests/test_graph_output_mode_ui.py`, `tests/test_process_run_node.py`, `tests/test_shell_run_controller.py`, `docs/specs/work_packets/project_managed_files/P11_process_run_output_mode_ui_WRAPUP.md`
- Artifacts Produced: `ea_node_editor/nodes/builtins/integrations_process.py`, `ea_node_editor/ui/support/node_presentation.py`, `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`, `tests/test_graph_output_mode_ui.py`, `tests/test_process_run_node.py`, `tests/test_shell_run_controller.py`, `docs/specs/work_packets/project_managed_files/P11_process_run_output_mode_ui_WRAPUP.md`

- Stored transcript shape: `stdout` and `stderr` emit staged refs shaped like `artifact-stage://generated.<workspace_id>.<node_id>.<port>` and stage into `.staging/artifacts/generated/process_run/generated.<workspace_id>.<node_id>.<port>.log` before later Save-time promotion.
- Failure cleanup: when stored mode raises on non-zero exit, the staged transcript files and their `metadata.artifact_store.staged` entries are both removed so no broken transcript refs remain in the runtime store.
- Surface wording: the inline quick control uses `memory` / `stored`, and the node chip reads `Inline capture` for memory mode and `Stored transcripts` for stored mode.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest tests/test_process_run_node.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_process_run_node.py tests/test_graph_output_mode_ui.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_process_run_node.py tests/test_shell_run_controller.py tests/test_graph_output_mode_ui.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing

1. Launch the shell UI, add a `Process Run` node, and confirm the inline row now exposes an `Output Mode` quick control with a chip that starts as `Inline capture`.
2. Leave the node in `memory` mode, run a simple command such as `python -c "print('hello')"` through the node, and confirm the workflow completes with the current inline stdout/stderr behavior unchanged.
3. Switch the inline control to `stored` and confirm the chip changes to `Stored transcripts` without needing the inspector.
4. In `stored` mode, connect `Process Run.stdout` to `File Read.path`, run `python -c "print('stored_output_from_artifact')"`, and confirm the downstream `File Read` node resolves and reads the transcript text successfully.
5. Keep `stored` mode enabled, run a command that writes stderr and exits non-zero, and confirm the run fails without leaving a reusable stored transcript ref behind for that failed attempt.

## Residual Risks

- Stored-mode failures now discard both the transcript files and the staged metadata entries; the raised error still preserves only a bounded stderr tail rather than keeping failed-run artifacts for inspection.
- The inline quick control and chip are packet-scoped to `Process Run`; later heavy-output adopters still need their own explicit UI/runtime adoption.

## Ready for Integration

- Yes: `Process Run` now has a packet-owned `memory` / `stored` contract, stored mode emits staged transcript refs, and the node surface exposes the required quick control plus status chip with packet verification passing.
