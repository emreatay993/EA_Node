# CTRL_CANVAS_INSERT_MENU P01: Text Annotation Contract and Typography

## Objective
- Add `passive.annotation.text`, extend passive-node typography styling, and lock a minimal text-annotation render contract before the new Ctrl-canvas insert menu consumes it.

## Preconditions
- `P00` is marked `PASS` in [CTRL_CANVAS_INSERT_MENU_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_STATUS.md).
- No later `CTRL_CANVAS_INSERT_MENU` packet is in progress.

## Execution Dependencies
- `P00`

## Target Subsystems
- `ea_node_editor/nodes/builtins/passive_annotation.py`
- `ea_node_editor/passive_style_normalization.py`
- `ea_node_editor/ui/dialogs/passive_style_controls.py`
- `ea_node_editor/ui/dialogs/passive_node_style_dialog.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphAnnotationNoteSurface.qml`
- `tests/test_planning_annotation_catalog.py`
- `tests/test_registry_filters.py`
- `tests/test_passive_property_editors.py`
- `tests/test_window_library_inspector.py`
- `tests/test_passive_style_dialogs.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/main_window_shell/passive_style_context_menus.py`

## Conservative Write Scope
- `ea_node_editor/nodes/builtins/passive_annotation.py`
- `ea_node_editor/passive_style_normalization.py`
- `ea_node_editor/ui/dialogs/passive_style_controls.py`
- `ea_node_editor/ui/dialogs/passive_node_style_dialog.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphAnnotationNoteSurface.qml`
- `tests/test_planning_annotation_catalog.py`
- `tests/test_registry_filters.py`
- `tests/test_passive_property_editors.py`
- `tests/test_window_library_inspector.py`
- `tests/test_passive_style_dialogs.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/main_window_shell/passive_style_context_menus.py`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/P01_text_annotation_contract_and_typography_WRAPUP.md`

## Required Behavior
- Register `passive.annotation.text` under the existing `Annotation` category with `display_name="Text"`, `runtime_behavior="passive"`, `surface_family="annotation"`, `surface_variant="text"`, no ports, `collapsible=False`, and a multiline `body` property defaulting to `"Text"`.
- Keep sticky note, callout, section header, and comment backdrop contracts unchanged.
- Extend the annotation variant metrics and renderer with a minimal text presentation: no visible header chrome, body text is the primary content, and selection styling remains clear even when the default fill is visually minimal.
- Extend passive-node style normalization, dialog controls, clipboard copy/paste/reset, and shared host rendering properties with:
  - `font_family: str`
  - `font_italic: bool`
  - `text_wrap: bool`
  - `text_align: "left" | "center" | "right" | "justify"`
  - `line_height: float`
- Keep the existing passive-node `Edit Style...` entry point intact so `Edit Style...`, reset, copy, and paste all round-trip the new typography fields through the current passive-style dialog/context-menu flow.
- Keep existing passive style fields for colors, border, radius, size, and bold stable and backward-compatible.
- Add inherit-capable dialog controls for font family, italic, wrap mode, horizontal alignment, and line height.
- Rendered text must honor font family, size, bold, italic, wrap, alignment, and line height for the new text annotation surface.
- The new text annotation must appear in registry/category/canvas-insert discovery paths, but connection quick insert must still exclude it because the node has no ports.

## Non-Goals
- No Ctrl+double-click insert menu or shell overlay work yet. `P02` owns that entry path.
- No inline editor auto-open or body double-click reopen yet. `P03` owns that workflow.
- No stylus placeholder behavior yet. `P02` owns it.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_planning_annotation_catalog tests.test_registry_filters tests.test_passive_property_editors tests.test_window_library_inspector tests.test_passive_style_dialogs tests.test_passive_graph_surface_host tests.main_window_shell.passive_style_context_menus -v`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_planning_annotation_catalog.py tests/test_passive_style_dialogs.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/ctrl_canvas_insert_menu/P01_text_annotation_contract_and_typography_WRAPUP.md`

## Acceptance Criteria
- The default registry exposes `passive.annotation.text` as a zero-port passive annotation node with `surface_variant="text"` and a `body` textarea property defaulting to `"Text"`.
- Passive-node `Edit Style...`, reset, copy, and paste flows can carry the new typography fields without regressing existing passive-node style behavior.
- The text-annotation render contract uses body text as the primary content, stays visually selectable, and honors the typography style fields.
- Canvas-insert discovery can surface the new text node, while connection quick insert still excludes it because the node has no compatible ports.

## Handoff Notes
- `P02` consumes the new `passive.annotation.text` type id directly. Do not rename the type id, `surface_variant`, or the typography field keys after this packet.
- `P03` inherits `tests/test_passive_graph_surface_host.py` and `GraphAnnotationNoteSurface.qml` as regression anchors when inline editing changes the text surface behavior. Do not leave those earlier anchors stale.
