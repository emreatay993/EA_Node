# Media, Image, Video, PDF, And Mail Nodes

## Purpose
Use this for passive media surfaces, image/video/PDF/mail nodes, video playback refocus, and fullscreen media. The `editSource` toolbar action on each surface routes to the native file dialog via `host.browseNodePropertyPath`; image/video/PDF/mail source editing uses a Source storage dropdown that passes `managed_copy` or `external_link` to choose project-managed storage or a direct external path for that browse action. External local media paths also expose `internalizeSource`, which routes through `host.internalizeNodePropertyPath` to copy the current file into project-managed storage without reopening Browse. Generic Source/open requests must pass the current value-derived mode, not rely on app-wide browse defaults.

## Start Here
- `ea_node_editor/nodes/builtins/passive_media.py`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewPlaceholder.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewViewport.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMailPanelSurface.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeFloatingToolbar.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphVideoPanelSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphVideoPanelFullscreenSurface.qml`
- `ea_node_editor/ui/mail_preview_provider.py`
- `ea_node_editor/ui/media_preview_provider.py`
- `ea_node_editor/ui/video_trim.py`
- `ea_node_editor/ui/project_review_deck.py`
- `ea_node_editor/ui_qml/ContentFullscreenOverlay.qml`
- `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
- `tests/main_window_shell/passive_image_nodes.py`
- `tests/main_window_shell/passive_pdf_nodes.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_mail_preview_provider.py`
- `tests/test_project_review_deck.py`
- `tests/test_content_fullscreen_bridge.py`
- `tests/test_video_trim.py`

## Notes
- Image/PDF/video/mail source browse filters are declared on each media node's `source_path` `PropertySpec.file_filter`; shell browse code should only forward that metadata.
- Media source storage checked state is derived in QML with `SourceStorageModeUtils.js`: `temp://` and `saved://` refs mean Internal, other values mean External. The inspector receives the matching `path_current_source_mode` from `window_library_inspector.py`. The media `internalizeSource` action must commit the returned `temp://` value so the floating-toolbar source popover and inspector Source storage combo flip to Internal from the value, not from separate UI state.
- Clipboard paste fallback creates existing media nodes by setting `passive.media.image_panel.source_path`, `passive.media.pdf_panel.source_path`, `passive.media.video_panel.source_path`, or `passive.media.mail_panel.source_path`. Local files and clearly media-typed remote URLs are direct source values; raw screenshots/PDF/video bytes are staged as node-owned `temp://` artifacts first.
- Image/PDF/video graph surfaces expose shared floating-toolbar chrome toggles for content-only, title, and frame. The toggles persist hidden `show_title` / `show_frame` node properties; crop remains Image Panel-only.
- Mail Panel graph surfaces render `mail_preview_provider.py` output through WebEngine with scripts/plugins disabled and remote resources allowed; `.eml` is parsed with stdlib email, while `.msg`/`.oft` rich preview is Windows/Outlook COM-backed and degrades to an unavailable/error state when Outlook or pywin32 is absent. Inline Mail preview is render-only so graph drag/select/resize stays owned by the node host; fullscreen Mail uses the generated preview URL, not the original `.eml`/`.msg`/`.oft` source URL, and owns Mail-specific Page/Width/100% zoom controls in `ContentFullscreenOverlay.qml`.
- Image crop is an Image Panel-only toolbar action backed by hidden `crop_x`, `crop_y`, `crop_w`, and `crop_h` properties. The crop-mode `Save` control and `save_crop_image` toolbar action bake the current crop into a node-owned internal PNG via `GraphCanvasCommandBridge.request_save_image_crop_replace` and reset crop fields to full image. Image rotate/mirror toolbar actions persist hidden `rotation_degrees`, `mirror_horizontal`, and `mirror_vertical` properties and render in `GraphMediaPanelPreviewViewport.qml`; `lock_aspect_ratio` is another hidden Image Panel toolbar toggle, but its proportional resize behavior lives in `GraphNodeResizeHandle.qml`. PDF Panel shares `GraphMediaPanelSurface.qml` but must not publish these image-only actions.
- Non-PDF image panels use `sourceImageProbe` for readiness/source dimensions and `appliedImage` for display; `previewImage` is PDF-only so normal images do not decode twice. Keep non-PDF image loading asynchronous and preserve natural source dimensions for crop math.
- Animated image classification is content-based in `media_preview_provider.describe_local_image(...)`: `QImageReader.supportsAnimation()` plus more than one frame selects the animated path, while static images, single-frame GIFs, corrupt files, and unsupported codecs stay on the provider-backed first-frame path. `GraphMediaPanelPreviewViewport.qml` creates one loader-owned `AnimatedImage` only for confirmed animated media, keeps it stable across hover/selection and buffered off-screen retention, uses `cache: false`, and plays only when the panel is selected or hovered, `host.inVisibleViewport` is true, the app preference and `animation_playback_mode` allow it, and proxy/crop/fullscreen does not own playback. Animated images consume the generic host fact; media surfaces do not own viewport geometry. Fullscreen always plays its own resolved-file renderer and pauses/resets inline playback.
- PDF Panel page metadata is refreshed state in `GraphMediaPanelSurface.qml`; do not turn it back into a one-shot readonly bridge binding or the inline `Page n / total` badge can stay stale after file load.
- PDF page navigation is split by surface: inline floating toolbar exposes `pdf_page_navigation` with a `pdf_page` popover, canvas Left/Right routes selected PDF nodes through the bridge, and fullscreen PDF uses QML `PdfDocument`/`PdfMultiPageView` from `ContentFullscreenOverlay.qml` against `media_payload.resolved_source_url`. Fullscreen PDF owns reader controls there as well: find text, match navigation, zoom, fit page/width/actual size, rotate, first/last page, and Page Up/Page Down shortcuts.
- Large PDFs must stay incremental: `pdf_preview_provider.py` caches page count separately and reads only the requested inline preview page size; fullscreen PDF should use `PdfMultiPageView` document navigation and clear the `PdfDocument` source when the overlay closes so local PDF files are not left locked. Non-QML consumers such as Project Review Deck export should use `render_pdf_page_image(...)` and pass the PDF Panel's persisted `page_number` so evidence slides show the user's current page, with the preview metadata path clamping out-of-range values.
- Video Panel bookmarks and clip range are inspector-visible node properties (`timeline_bookmarks`, `clip_enabled`, `clip_start_ms`, `clip_end_ms`) and also have inline toolbar controls in `GraphVideoPanelSurface.qml`. The bookmark toolbar list is a `video_bookmarks` popover layout in `GraphNodeFloatingToolbar.qml`; fullscreen mirrors markers and range controls in `GraphVideoPanelFullscreenSurface.qml`.
- Video frame capture and timestamp notes are QML-triggered but Python-created through `GraphCanvasCommandBridge` and `GraphCanvasPresenter`: captured frames stage PNG bytes into a new Image Panel sized from the source Video Panel's current host width/height through the Image Panel `custom_width` / `custom_height` path, while timestamp notes create Text annotations with `corex-link` node links carrying `video_position_ms=<ms>` metadata. `GraphSceneCommandBridge.open_node_link` seeks Video Panel targets when that metadata is present; `GraphVideoPanelSurface.qml` must keep deferred initial-position handling so links created from a zero-position video still seek when a later timestamp arrives.
- Video trim-save actions are QML-triggered but Python-created through `GraphCanvasCommandBridge` / `ContentFullscreenBridge` into `GraphCanvasPresenter` and `ea_node_editor/ui/video_trim.py`. Replace stages an MP4 clip back into the same Video Panel, Copy creates a new Video Panel, bookmarks inside the selected range are remapped to clip-relative positions, and the helper tries ffmpeg stream copy before falling back to precise H.264/AAC encoding.
- Clip range uses the existing Loop state: full-video loop remains `MediaPlayer.Infinite` only when no clip range is active; with an active clip range, loop repeats the selected in/out span.
- Inline Video Panel playback must not be gated by graph selection. Playing or selecting a second canvas Video Panel should not pause the first inline player; fullscreen handoff still pauses the inline player for the same node so the fullscreen surface owns that playback.
- The stored `unfocused_behavior` Video Panel property is kept for saved-project compatibility but hidden from the inspector; do not use it to pause inline playback on selection changes.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_passive_image_nodes.py tests/test_pdf_preview_provider.py tests/test_content_fullscreen_bridge.py tests/main_window_shell/passive_image_nodes.py tests/main_window_shell/passive_pdf_nodes.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_mail_preview_provider.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_project_review_deck.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_video_trim.py tests/test_icon_registry.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/serializer/round_trip_cases.py -q
.\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py -k "content_fullscreen_overlay_renders_pdf_media or content_fullscreen_overlay_owns_animated_image_playback" --ignore=venv -q
```

## Breadcrumbs
- [Passive, Media, And Tabular Surfaces](../subsystems/passive_media_tabular_surfaces.md)
- [Viewer Session, Native Overlay, And Fullscreen](viewer_session_overlay_fullscreen.md)

## Update Triggers
Update when media node definitions, source browse filters, animated playback viewport gating, PDF/mail preview helpers, video focus behavior, fullscreen media, or media tests change.

## 2026-07-11 Performance Ownership

- Mail preview owns a bounded stamp-keyed LRU. PDF caching remains deferred; fullscreen media uses the retained loader owned by the viewer/fullscreen route.
