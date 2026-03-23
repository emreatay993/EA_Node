# PROJECT_MANAGED_FILES P11: Process Run Output Mode UI

## Objective
- Add the first concrete heavy-output adopter on `Process Run`: a user-controlled `memory` versus `stored` mode, inline quick-toggle/status-chip UX, and stored transcript output behavior built on the earlier artifact/runtime foundations.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P09`
- `P10`

## Target Subsystems
- `ea_node_editor/nodes/builtins/integrations_process.py`
- `ea_node_editor/ui/support/node_presentation.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`
- `ea_node_editor/ui_qml/components/graph/NodeCard.qml`
- `tests/test_process_run_node.py`
- `tests/test_shell_run_controller.py`
- `tests/test_graph_output_mode_ui.py`

## Conservative Write Scope
- `ea_node_editor/nodes/builtins/integrations_process.py`
- `ea_node_editor/ui/support/node_presentation.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`
- `ea_node_editor/ui_qml/components/graph/NodeCard.qml`
- `tests/test_process_run_node.py`
- `tests/test_shell_run_controller.py`
- `tests/test_graph_output_mode_ui.py`
- `docs/specs/work_packets/project_managed_files/P11_process_run_output_mode_ui_WRAPUP.md`

## Required Behavior
- Add a packet-owned `output_mode` contract for `Process Run` with the main user-facing choices `memory` and `stored`.
- Preserve existing behavior for `memory` mode so current inline stdout/stderr workflows remain usable.
- In `stored` mode, write the packet-owned transcript outputs into managed staging immediately and emit stored artifact refs instead of large inline strings.
- Add an inline quick control for the main mode and a visible status chip/badge reflecting the current state on the node surface.
- Keep advanced stored-output settings in the inspector rather than turning the surface into a full artifact editor.
- Add narrow regression coverage proving both output modes still work and the UI reflects mode/status changes correctly.

## Non-Goals
- No automatic switching to `stored` based on payload size.
- No expansion of the quick-toggle/status UX to every heavy-output node yet.
- No full artifact manager or bulk output browser.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_process_run_node.py tests/test_shell_run_controller.py tests/test_graph_output_mode_ui.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_process_run_node.py tests/test_graph_output_mode_ui.py --ignore=venv -q`

## Expected Artifacts
- `tests/test_graph_output_mode_ui.py`
- `docs/specs/work_packets/project_managed_files/P11_process_run_output_mode_ui_WRAPUP.md`

## Acceptance Criteria
- `Process Run` exposes a user-controlled `memory` versus `stored` mode.
- `memory` mode keeps the current inline-output behavior.
- `stored` mode stages transcript outputs immediately and emits artifact refs instead of large inline payload strings.
- The node surface exposes the quick mode control and a status chip/badge while advanced settings remain in the inspector.

## Handoff Notes
- `P12` inherits the exact mode names, badge wording, and transcript-output description for final docs and QA evidence.
- Record the concrete Process Run stored-output artifact shape in the wrap-up so later heavy-output adopters can remain consistent without copying UI behavior blindly.
