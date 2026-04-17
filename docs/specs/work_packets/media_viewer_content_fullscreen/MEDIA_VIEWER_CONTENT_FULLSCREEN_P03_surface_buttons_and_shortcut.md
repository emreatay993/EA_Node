# MEDIA_VIEWER_CONTENT_FULLSCREEN P03: Surface Buttons and Shortcut

## Objective

- Make content fullscreen discoverable from media/viewer node surfaces and keyboard-accessible from the graph canvas through `F11`.

## Preconditions

- `P00` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P01` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P02` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P04` may run in parallel with this packet after `P02` is `PASS`.

## Execution Dependencies

- `P01`
- `P02`

## Target Subsystems

- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewViewport.qml`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_viewer_surface_contract.py`
- `tests/graph_surface/media_and_scope_suite.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewViewport.qml`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_viewer_surface_contract.py`
- `tests/graph_surface/media_and_scope_suite.py`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P03_surface_buttons_and_shortcut_WRAPUP.md`

## Required Behavior

- Add a media fullscreen button using the existing `GraphSurfaceButton` pattern and the `fullscreen` icon from `P02`.
- Show the media fullscreen button only when the preview is ready and the node is hovered or selected.
- Suppress the media fullscreen button while crop editing is active.
- Preserve and update `embeddedInteractiveRects` so the media fullscreen button receives clicks and does not trigger node drag, selection, resize, or crop gestures.
- Add a viewer fullscreen affordance to `GraphViewerSurface.qml`, replacing the inert `moreButton` behavior with a bridge-backed fullscreen request.
- Preserve viewer toolbar sizing, hover/selection behavior, and embedded interactive rect routing.
- Wire graph/canvas `F11` handling:
  - close fullscreen through `contentFullscreenBridge.request_close()` when fullscreen is already open
  - otherwise open the single selected eligible node through `contentFullscreenBridge.request_open_node(node_id)`
  - show the existing graph hint path when there is no single eligible selected node
- Keep `F11` scoped to content fullscreen. Do not wire OS/app-window fullscreen.
- Keep the surface implementation as a bridge consumer. Do not redefine media payload normalization or viewer lifecycle in QML.
- Add packet-owned tests whose names include `content_fullscreen` so the targeted verification commands remain stable.

## Non-Goals

- No shell overlay or media renderer changes except for consuming the existing bridge and icon contract.
- No native viewer widget retargeting.
- No double-click fullscreen gesture.
- No node context-menu fullscreen entry.
- No crop/page/source editing from fullscreen.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_contract.py tests/test_viewer_surface_contract.py tests/graph_surface/media_and_scope_suite.py -k content_fullscreen --ignore=venv -q`

## Review Gate

- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_controls.py -k content_fullscreen --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/media_viewer_content_fullscreen/P03_surface_buttons_and_shortcut_WRAPUP.md`

## Acceptance Criteria

- Media node previews expose a fullscreen button only when the preview is ready, the node is hovered or selected, and crop mode is inactive.
- Media fullscreen button clicks call the bridge without stealing graph drag/selection gestures.
- Viewer surfaces expose a fullscreen button that calls the bridge and keeps toolbar interactive rects accurate.
- `F11` closes an open overlay, opens exactly one selected eligible node when possible, and shows a graph hint otherwise.
- Existing graph canvas keyboard behavior and unrelated surface controls remain unchanged.

## Handoff Notes

- `P04` may run in parallel with this packet but must not edit the QML surface files or graph shortcut wiring owned here.
- If this packet changes the `contentFullscreenBridge` slot names or expected return values, it must stop and report that the change belongs in `P01` or requires an explicit P01 test handoff.
