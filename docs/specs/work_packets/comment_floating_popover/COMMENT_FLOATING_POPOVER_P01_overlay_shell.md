# COMMENT_FLOATING_POPOVER P01: Overlay Shell

## Packet Metadata

- Packet: `P01`
- Title: `Overlay Shell`
- Execution Dependencies: `none`
- Worker model: `gpt-5.5`
- Worker reasoning effort: `xhigh`

## Objective

- Add the QML-only floating popover shell for COREX comment backdrop nodes: transient canvas state, node-host anchoring, pan/zoom-following overlay mount, stable object names, visual styling, and non-action dismissal paths.

## Preconditions

- `P00` is complete and the packet docs are available on the target merge branch.
- The implementation base is current `main`.
- Existing comment backdrop rendering and inline `body` editing behavior are unchanged at packet start.

## Execution Dependencies

- none

## Target Subsystems

- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeOverlayToolbarLayer.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceTextareaEditor.qml`
- `tests/test_comment_backdrop_layer.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope

- `docs/specs/work_packets/comment_floating_popover/P01_overlay_shell_WRAPUP.md`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
- `tests/test_comment_backdrop_layer.py`
- `tests/test_main_window_shell.py`

## Required Behavior

- Add transient canvas state shaped as `activeCommentPopoverNodeId`, plus open/close/toggle helpers that are exposed through `GraphCanvas.qml`.
- Mount a new `GraphCommentFloatingPopover` under the graph overlay stack so it tracks the active comment backdrop host during pan, zoom, drag, and resize using the same world-layer anchoring model as existing node overlays.
- The panel must be invisible when no active comment popover node is set, when the active host is missing, when the active host is not a `comment_backdrop`, or when the graph is in a state where the host cannot safely anchor the panel.
- The panel must provide stable object names, including `graphCommentFloatingPopover`, `graphCommentFloatingPopoverCloseButton`, `graphCommentFloatingPopoverBodyEditor`, and `graphCommentFloatingPopoverBodyEditorField`.
- Match the design baseline: compact header with comment icon, node title, count pill, comment-yellow accent, panel-alt background, border, 8px radius, strong shadow, scrollable body, footer editor, and close button.
- Reuse `GraphSurfaceTextareaEditor` for the footer editor shell where practical, but do not wire substantive body commits beyond the existing QML signal contract in this packet.
- Add dismissal shell behavior for the close button, Escape, click-away/canvas press, and active host loss.
- Keep the state transient. Do not add Python properties, serializer fields, preferences, or scene payload keys.

## Non-Goals

- Do not add toolbar, context-menu, or surface-action entry points. `P02` owns opening the popover from comment-specific actions.
- Do not change `Peek Inside`, comment peek state, subnode `scope_path`, or focused-view behavior.
- Do not add a separate comment-thread data model.
- Do not change `GraphNodeHost.commonNodeActions`.
- Do not implement broad regression closeout beyond the packet-owned QML load and boundary checks.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_comment_backdrop_layer.py tests/test_main_window_shell.py -k "comment_backdrop or overlay_host_item or graph_canvas_helper_components_hold_scene_surface_and_delegate_logic" --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_comment_backdrop_layer.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/comment_floating_popover/P01_overlay_shell_WRAPUP.md`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `tests/test_comment_backdrop_layer.py`
- `tests/test_main_window_shell.py`

## Acceptance Criteria

- A comment popover can be opened by setting the new transient active node id helper from QML/test code.
- The popover follows the target comment backdrop host across pan/zoom and disappears when the host is gone or inactive.
- Close button, Escape, and canvas click-away all clear `activeCommentPopoverNodeId`.
- The popover exposes the required object names and compiles as part of the GraphCanvas QML surface.
- No project document, preference, serializer, or scene payload output contains the popover state.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- `P02` will add the comment-specific action entry points and body commit wiring against the shell created here.
- If `P01` adds structural boundary assertions in `tests/test_main_window_shell.py` or QML load assertions in `tests/test_comment_backdrop_layer.py`, `P03` inherits those regression anchors and may update them for final behavior coverage.
