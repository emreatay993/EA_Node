# P06 Node Footer Persistent Elapsed Rendering Wrap-Up

## Implementation Summary

- Packet: `P06`
- Branch Label: `codex/persistent-node-elapsed-times/p06-node-footer-persistent-elapsed-rendering`
- Commit Owner: `worker`
- Commit SHA: `d22ea53d858aba848c91ebea2b50362056a510dd`
- Changed Files: `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml`, `tests/test_shell_run_controller.py`, `tests/graph_surface/passive_host_interaction_suite.py`, `tests/graph_track_b/qml_preference_bindings.py`, `docs/specs/work_packets/persistent_node_elapsed_times/P06_node_footer_persistent_elapsed_rendering_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/persistent_node_elapsed_times/P06_node_footer_persistent_elapsed_rendering_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml`, `tests/test_shell_run_controller.py`, `tests/graph_surface/passive_host_interaction_suite.py`, `tests/graph_track_b/qml_preference_bindings.py`

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k persistent_node_elapsed_footer --ignore=venv -q` (verification command #1 and review gate)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k persistent_node_elapsed_footer --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py -k persistent_node_elapsed_footer --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: Open a workspace with a runnable node such as `core.logger`, and keep the graph canvas visible.
- Start a workflow run and confirm the node footer appears immediately with a live elapsed value while the node is actively running.
- Let the run complete or stop and confirm the footer stays visible with the quieter completed styling after the transient running/completed chrome clears.
- Rename or move the node and confirm the cached footer remains visible; then change an execution-affecting node property such as the logger `message` and confirm the footer clears immediately.
- Trigger a nonfatal failure while a node is running and confirm the footer disappears as soon as the node enters failure chrome.

## Residual Risks

- Windows pytest still emits the existing non-fatal temp-cleanup `PermissionError` against `pytest-current` after the QML subprocess suites finish successfully.

## Ready for Integration

- Yes: P06 stays inside the packet scope, switches the footer to the packet-owned canvas timing lookups, and passes the required verification plus review gate.
