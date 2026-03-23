# CTRL_CANVAS_INSERT_MENU P03: Text Inline Editing Workflow

## Objective
- Auto-open inline text editing after insertion, reuse body double-click reopen, and keep inspector and inline editing on the same `body` property for `passive.annotation.text`.

## Preconditions
- `P00` is marked `PASS` in [CTRL_CANVAS_INSERT_MENU_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_STATUS.md).
- No later `CTRL_CANVAS_INSERT_MENU` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`

## Target Subsystems
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceTextArea.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceTextareaEditor.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphAnnotationNoteSurface.qml`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/main_window_shell/passive_property_editors.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceTextArea.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceTextareaEditor.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphAnnotationNoteSurface.qml`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/main_window_shell/passive_property_editors.py`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/P03_text_inline_editing_workflow_WRAPUP.md`

## Required Behavior
- Reuse the existing pending-surface-action pattern end-to-end so, after a successful `Text` insertion from `P02`, the selected `passive.annotation.text` node auto-opens an inline multiline body editor through the current `GraphSceneBridge` / `GraphCanvas.qml` handoff instead of a new canvas edit channel.
- Reuse the current passive-surface `nodeOpenRequested` pattern so body double-click reopens inline editing without adding a second canvas-level edit API.
- Keep the selected node editable in the inspector textarea at the same time by committing inline edits through the shared `body` property path; inspector and inline editors must stay in sync.
- When the auto-opened editor is showing the default `"Text"` content, select that default text so immediate typing replaces it.
- Editor focus must publish embedded interactive rects and prevent drag/open/context leakage; `Ctrl+Enter` commits and `Esc` resets.
- The inline editor must mirror `font_family`, font size, bold, italic, wrap mode, and horizontal alignment from the passive text style. `line_height` remains display-only because Qt `TextArea` does not support it.
- Keep the packet-local auto-open rule non-persistent. Do not add a new serialized node property just to track first-open selection behavior.

## Non-Goals
- No new shell overlay or canvas command API beyond using the existing pending-surface-action bridge.
- No new stylus behavior beyond the `P02` placeholder.
- No new text-node schema beyond the `P01` node contract and typography style fields.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_inline.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/drop_connect_and_workflow_io.py tests/main_window_shell/passive_property_editors.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_inline.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/ctrl_canvas_insert_menu/P03_text_inline_editing_workflow_WRAPUP.md`

## Acceptance Criteria
- Choosing `Text` from the Ctrl-canvas insert menu creates the node and auto-opens the inline multiline body editor.
- Body double-click reopens inline editing through the existing `nodeOpenRequested` seam.
- Inline-editor focus and shortcuts do not leak drag/open/context behavior to the host, and the editor publishes embedded interactive rects while active.
- Inspector editing and inline editing stay in sync through the same `body` property.
- The inline editor mirrors the passive typography fields except `line_height`.

## Handoff Notes
- This packet inherits `tests/main_window_shell/drop_connect_and_workflow_io.py` from `P02`. Update that earlier shell regression anchor in-place rather than adding a duplicate later shell test for the same insert outcome.
- Record the object names, one-shot default-text-selection rule, and the exact pending-surface-action consumption path in the wrap-up so `P04` can document the final behavior accurately.
