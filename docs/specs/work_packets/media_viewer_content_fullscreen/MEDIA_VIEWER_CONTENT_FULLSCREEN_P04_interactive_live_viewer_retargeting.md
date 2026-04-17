# MEDIA_VIEWER_CONTENT_FULLSCREEN P04: Interactive Live Viewer Retargeting

## Objective

- Retarget the existing native DPF viewer overlay host into the fullscreen viewport while fullscreen is open, then restore the same widget to the node viewport on close.

## Preconditions

- `P00` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P01` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P02` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P03` may run in parallel with this packet after `P02` is `PASS`.

## Execution Dependencies

- `P01`
- `P02`

## Target Subsystems

- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `tests/test_viewer_host_service.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `tests/test_content_fullscreen_bridge.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `tests/test_viewer_host_service.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `tests/test_content_fullscreen_bridge.py`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P04_interactive_live_viewer_retargeting_WRAPUP.md`

## Required Behavior

- Extend `ViewerHostService` and `EmbeddedViewerOverlayManager` so a single active `(workspace_id, node_id)` can be pinned to a fullscreen target while the bridge is open.
- Locate fullscreen geometry from the QML item with `objectName: "contentFullscreenViewerViewport"` when that target is active.
- Reuse the existing native viewer widget/session for the node. Do not create a second live viewer widget for fullscreen.
- Retarget geometry, z-order, visibility, focus, and input routing to the fullscreen viewport while active.
- Restore the widget to the node viewport when fullscreen closes, the workspace changes, the node is deleted, the viewer session ends, or geometry becomes invalid.
- Keep proxy/status fallback behavior when a live viewer is still opening, blocked, or unavailable.
- Avoid orphaned overlay containers or stale native widgets after repeated open/close cycles.
- Keep the viewer host API additive and compatible with existing node-embedded viewer behavior.
- Add packet-owned tests whose names include `content_fullscreen` so the targeted verification commands remain stable.

## Non-Goals

- No QML shell overlay layout changes except through the existing `contentFullscreenViewerViewport` contract.
- No media button, viewer toolbar, or `F11` shortcut changes.
- No new viewer backend, camera-control redesign, or workflow rerun behavior.
- No second native viewer widget for fullscreen.
- No saved-project schema or persistence changes.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_host_service.py tests/test_embedded_viewer_overlay_manager.py tests/test_content_fullscreen_bridge.py -k content_fullscreen --ignore=venv -q`

## Review Gate

- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py -k content_fullscreen --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/media_viewer_content_fullscreen/P04_interactive_live_viewer_retargeting_WRAPUP.md`

## Acceptance Criteria

- A live viewer node can retarget its existing native widget to `contentFullscreenViewerViewport` while fullscreen is open.
- Closing fullscreen restores the same widget to the node viewport.
- Viewer sessions still embedded in nodes keep existing geometry behavior when fullscreen is closed.
- Blocked/unavailable viewer states render through proxy/status fallback instead of creating orphaned widgets.
- Workspace switch, node deletion, and repeated open/close cycles do not leave stale overlay containers.
- `tests/test_content_fullscreen_bridge.py` remains current if this packet extends or revises the viewer payload/lifecycle contract from `P01`.

## Handoff Notes

- `P03` may run in parallel with this packet but must not edit viewer host service or embedded viewer overlay manager code.
- If this packet needs to rename `contentFullscreenViewerViewport`, it must inherit and update the `P02` overlay tests and coordinate with the executor before proceeding because that object name is a cross-packet locked default.
