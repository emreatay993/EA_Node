# VERIFICATION_SPEED P04: GUI Wait Helper Cleanup

## Objective
- Replace fixed sleeps and ad hoc event-pump polling in the slow GUI tests with shared wait helpers so the suite pays less unconditional delay while preserving the current UI behavior checks.

## Preconditions
- `P00` is marked `PASS` in [VERIFICATION_SPEED_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md).
- No later `VERIFICATION_SPEED` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- a new shared test helper module under `tests/` for event-pumped waits
- `tests/main_window_shell/view_library_inspector.py`
- `tests/main_window_shell/passive_image_nodes.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope
- `tests/qt_wait.py`
- `tests/main_window_shell/view_library_inspector.py`
- `tests/main_window_shell/passive_image_nodes.py`
- `tests/test_passive_graph_surface_host.py`

## Required Behavior
- Add a shared helper for waiting on GUI conditions by repeatedly processing events until a predicate passes or a timeout expires.
- Replace the fixed `QTest.qWait(...)` usage and the local `_wait_for_pane_width(...)` busy-loop pattern in the packet-owned tests with the shared helper.
- Preserve the current timeout envelopes unless a narrower value is justified by the existing observable state transitions.
- Preserve current assertions, current user-visible behavior checks, and current shell/QML isolation assumptions.
- Keep the cleanup entirely in tests. No production QML, Python runtime, or timer-interval changes belong in this packet.

## Non-Goals
- No runner, marker, or collection-hygiene changes.
- No production performance tuning in `ea_node_editor/**`.
- No expansion into unrelated GUI tests beyond the packet-owned files.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host.PassiveGraphSurfaceHostTests.test_graph_canvas_temporarily_simplifies_node_shadow_during_wheel_zoom -v`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellViewLibraryInspectorTests.test_qml_side_panes_share_collapsible_shell_behavior -v`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellViewLibraryInspectorTests.test_qml_workspace_tabs_allow_leftward_drag_from_non_leftmost_slots -v`
4. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellPassiveImageNodesTests.test_image_panel_crop_handles_report_expected_cursor_and_hover -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellViewLibraryInspectorTests.test_qml_side_panes_share_collapsible_shell_behavior -v`

## Expected Artifacts
- `docs/specs/work_packets/verification_speed/P04_gui_wait_helper_cleanup_WRAPUP.md`

## Acceptance Criteria
- The packet-owned tests use the shared helper instead of raw fixed sleeps for the targeted waits.
- The verification commands pass unchanged in behavior.
- No production files under `ea_node_editor/**` are modified.

## Handoff Notes
- Keep the helper generic and packet-local to tests. Do not couple it to the future runner script.
- `P05` will document the new workflow; do not add user-facing docs in this packet.
