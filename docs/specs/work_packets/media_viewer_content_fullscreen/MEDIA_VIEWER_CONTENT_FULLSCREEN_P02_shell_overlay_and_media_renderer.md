# MEDIA_VIEWER_CONTENT_FULLSCREEN P02: Shell Overlay and Media Renderer

## Objective

- Add the in-app fullscreen overlay to the shell, render image/PDF media payloads in fullscreen, and register the shared fullscreen icon/viewport contract consumed by later surface and viewer packets.

## Preconditions

- `P00` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P01` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- No later `MEDIA_VIEWER_CONTENT_FULLSCREEN` packet is in progress.

## Execution Dependencies

- `P01`

## Target Subsystems

- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/ContentFullscreenOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/icons/fullscreen.svg`
- `ea_node_editor/ui/icon_registry.py`
- `tests/test_icon_registry.py`
- `tests/test_shell_window_lifecycle.py`
- `tests/main_window_shell/shell_runtime_contracts.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/ContentFullscreenOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/icons/fullscreen.svg`
- `ea_node_editor/ui/icon_registry.py`
- `tests/test_icon_registry.py`
- `tests/test_shell_window_lifecycle.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P02_shell_overlay_and_media_renderer_WRAPUP.md`

## Required Behavior

- Add `ContentFullscreenOverlay.qml` and instantiate it from `MainShell.qml` above normal shell/graph content when `contentFullscreenBridge.open` is true.
- Keep the overlay inside the app window. Do not use OS fullscreen, a separate top-level window, or a modal dialog.
- Make the overlay cover the content area, capture focus while open, block background pointer interaction, and close through `Esc`, `F11`, and a close button.
- Render a compact top bar with the node title and an `Esc / F11` close hint.
- Render image media and PDF media from the `contentFullscreenBridge.media_payload` state using the same source, crop, page, preview, and fit semantics as the node preview.
- Provide local fullscreen display modes `Fit`, `Fill`, and `100%` without mutating node crop/source/page/fit state.
- Render a stable viewer placeholder area for `viewer_payload` with `objectName: "contentFullscreenViewerViewport"` so `P04` can target the native widget there.
- Show proxy/status text for viewer payloads until `P04` adds live native retargeting.
- Add a `fullscreen` UI icon to `ea_node_editor/ui/icon_registry.py` and add the corresponding shell SVG asset.
- Keep all QML text within parent bounds and avoid layout shifts when payload/status changes.
- Add packet-owned tests whose names include `content_fullscreen` so the targeted verification commands remain stable.

## Non-Goals

- No media or viewer surface button changes.
- No `F11` open-from-selection behavior outside the overlay close path.
- No native viewer widget retargeting.
- No PDF page editing, crop editing, media file picker, or node property mutation from fullscreen.
- No saved-project schema or persistence changes.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_icon_registry.py tests/test_shell_window_lifecycle.py tests/main_window_shell/shell_runtime_contracts.py -k content_fullscreen --ignore=venv -q`

## Review Gate

- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py -k content_fullscreen --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/media_viewer_content_fullscreen/P02_shell_overlay_and_media_renderer_WRAPUP.md`
- `ea_node_editor/ui_qml/ContentFullscreenOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/icons/fullscreen.svg`

## Acceptance Criteria

- `MainShell.qml` renders the fullscreen overlay only while the bridge is open.
- Escape and F11 close an already open overlay through `contentFullscreenBridge.request_close()`.
- Background graph and shell controls do not receive pointer events while the overlay is open.
- Image and PDF payloads render through the fullscreen overlay without mutating graph node state.
- The viewer placeholder exposes `objectName: "contentFullscreenViewerViewport"` for later native retargeting.
- The `fullscreen` icon is registered and loadable through the existing icon registry tests.

## Handoff Notes

- `P03` consumes the `fullscreen` icon and bridge-driven close/open contract. If P03 changes icon naming, it must inherit and update `tests/test_icon_registry.py`.
- `P04` consumes the `contentFullscreenViewerViewport` object name. Any rename after this packet must inherit and update this packet's overlay tests plus `P04` viewer host tests.
