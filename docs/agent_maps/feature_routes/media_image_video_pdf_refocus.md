# Media, Image, Video, PDF, And Mail Nodes

## Purpose
Use this for the active unified Media Panel, its derived image/PDF/video renderers, effective-source authority, media creation/actions, fullscreen media, and the separate passive Mail Panel.

## Start Here
- `ea_node_editor/nodes/builtins/media_panel.py`
- `ea_node_editor/nodes/builtins/passive_mail.py`
- `ea_node_editor/nodes/file_dialog_filters.py`
- `ea_node_editor/ui/media_panel_source.py`
- `ea_node_editor/ui/media_panel_presentation.py` — canvas-only previous Plot preview, identity/route binding and update status
- `tests/test_media_panel_presentation.py`
- `ea_node_editor/ui/xy_plot_session.py`
- `ea_node_editor/web_host/xy_transport.py`
- `ea_node_editor/ui_qml/components/web/XYPlotHost.qml`
- `tests/test_xy_fullscreen_bridge.py`
- `tests/test_xy_plot_qml.py`
- `ea_node_editor/ui/media_video_state.py`
- `ea_node_editor/ui/shell/media_panel_action_service.py`
- `ea_node_editor/ui/media_preview_provider.py`
- `ea_node_editor/ui/pdf_preview_provider.py`
- `ea_node_editor/ui/preview_image_ids.py` — single encode/decode codec for local image/PDF preview provider ids
- `ea_node_editor/ui/video_trim.py`
- `ea_node_editor/ui/project_review_deck.py`
- `ea_node_editor/ui_qml/graph_canvas_state/execution_state_props.py`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaImageRenderer.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaImageViewport.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPdfRenderer.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaVideoRenderer.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaVideoFullscreenRenderer.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaVideoPlaybackCore.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMailPanelSurface.qml`
- `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
- `ea_node_editor/ui_qml/ContentFullscreenOverlay.qml`
- `tests/test_media_panel.py`
- `tests/test_media_panel_creation_preferences.py`
- `tests/test_media_panel_source_resolution.py`
- `tests/test_media_panel_qml_surface.py`
- `tests/test_media_video_state.py`
- `tests/test_media_panel_action_service.py`
- `tests/fixtures/media/video-playback.mp4` — synthetic decoded-media lifecycle fixture
- `tests/test_content_fullscreen_bridge.py`
- `tests/test_passive_image_nodes.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_preview_image_ids.py` — QML-engine round trip of published preview URLs for paths containing # or %XX
- `tests/test_project_review_deck.py`
- `tests/main_window_shell/passive_image_nodes.py`
- `tests/main_window_shell/passive_pdf_nodes.py`

## Source And Runtime Rules
- `media.panel` is one active sink with an optional exposed `source` input and private `_surface_source` output. The accepted input union is Path, String, exact `ImageValue`, or exact `PlotValue`; runtime cardinality is one Item and the input never uses the authored property as an execution default.
- Source input exposure selects authority. Hidden means the authored `source` property is used without a run. Exposed means only settled connected input is considered, including when unwired or non-ready; never fall back to the dormant property.
- `ui/media_panel_source.py` remains the strict Python authority for actions, Project Review Deck and fullscreen. Only `ready` publishes current URLs/raw values. The canvas lookup adds a separate `previous_plot_preview` through `ui/media_panel_presentation.py`; it never turns a stale result into current data.
- Canvas Plot updates retain the last observed immutable preview with an upper-right Updating icon; idle Manual/Stop shows an Out of date icon. Metadata binds the exact observed record, producer, source route and actual project/workspace lifetime. Failure/empty/unavailable output, source rewiring/removal and context replacement clear the preview. A guarded active-update fallback covers newer CURRENT facts whose cache entry has not arrived; it reads the bound prior entry in the existing bounded UI cache, not arbitrary history.
- `GraphMediaPanelSurface.qml` distinguishes current source/action readiness from display readiness. `GraphMediaImageViewport.qml` switches actual image buffers only after successful decode, rejecting superseded/cancelled requests and clearing decode failures. Old pixels cannot enable crop/export/fullscreen. The shared `GraphNodeHeaderLayer.qml` reuses diagnostic badge geometry and tooltip policy; no body text obscures the plot during regeneration.
- Connected runtime media resolves only the output cache entry named by the node's retained solution fact. An expired retained record projects `stale` without rendering; expired-without-record and never-run nodes expose no cached source. Fullscreen, graph commands/presenters, and Project Review Deck inherit this one selector through `resolve_media_panel_source(...)`.
- `nodes/file_dialog_filters.py` owns the shared image/PDF/video suffixes, combined filter, and source classification. Do not recreate suffix tables in clipboard, drop, or preview consumers.
- Connected `ImageValue` uses `image_value_preview_source()`; bytes never enter QML. Matching immutable content reuses its active-provider URL before decoding/publication, preserving the Media renderer during geometry/formatting refreshes. Cache loss, provider replacement and changed content still register normally; mutable viewer previews keep their revision semantics. Project Review Deck materializes images only inside its existing temporary export area.
- Connected `PlotValue` preserves its complete session data while using `preview` for the existing image renderer. Fullscreen dispatches to the dedicated XY QML host with lightweight session metadata. `XYPlotSessionOwner` owns producer guards, close-time optional axis writeback and temporary geometry caches; generic plot-node hosting is unchanged. Running/failed/unavailable producers retire interactive sessions even before the Media Panel itself runs.

## Surface And Action Rules
- `GraphMediaPanelSurface.qml` is the common dispatcher. It owns Source/Browse/Internalize/Repair/Open, Source exposure, title/frame, and fullscreen actions; the three renderers own mode-specific behavior.
- `MediaPanelActionService` owns crop, frame creation, timestamp annotation, trim replace/copy, artifact staging, normalized result payloads, and the lazy trim worker/QThread map. `GraphCanvasCommandBridge` has a dedicated concrete media-action source, and `ContentFullscreenBridge` receives only the service's two trim callbacks.
- Input exposure disables the inspector Source editor, Browse, Internalize, Repair, crop Save/Replace, and trim Replace. Display actions, Open Source, fullscreen, frame capture, and valid trim Copy remain mode-gated.
- Image crop/transform/animation state remains in `GraphMediaImageRenderer.qml`; animation ownership is loader-local and pauses/releases on proxy, crop, offscreen, fullscreen, source, or mode transitions.
- PDF inline preview owns page clamping through `pdf_preview_provider.py`; fullscreen uses `PdfDocument`/`PdfMultiPageView`. Graph mutation does not rewrite authored page values.
- Local image and PDF previews share the `image://<provider>/preview?key=value` id format. Python builds them through `media_preview_provider.local_image_preview_url` and the PDF description's `preview_url`; QML builds local-media-preview ids through `GraphMediaPanelSourceUtils.js` `previewSourceUrl` with `encodeURIComponent`. Both providers decode only through `ui/preview_image_ids.py`, exactly once, because Qt passes the query still encoded: a second decode turns a file URL's `%23` into a fragment, so paths containing `#` or `%XX` fail inline. Prove changes by loading a published URL for such a path through a QML engine, not with hand-built ids.
- `GraphMediaVideoPlaybackCore.qml` owns the shared per-renderer player/audio, source lifecycle, seek, clip, bookmark, marker, thumbnail-primer, rate/time, and transient-state behavior. Inline retains graph-property persistence, node/capture/timestamp actions, selection/autoplay, and artifact release; fullscreen retains controls, trim calls, resume, and close-state handoff. `ui/media_video_state.py` is the single Python normalization owner.
- Same-node fullscreen ownership clears the corresponding inline core source so only fullscreen decodes it; other inline video nodes retain independent loaded/playing cores. Closing/reopening restores paused or playing position, and nonzero paused handoffs skip thumbnail priming.
- Inline and fullscreen consume the same effective source. Fullscreen uses `content_kind="media"` with dynamic `media_payload.media_kind` and refreshes on execution, topology, exposure, node, or workspace changes.
- Fullscreen receives the live `ShellRunState` and execution signal from composition rather than reading `ShellWindow`. Its direct bridge tests pin retained `NodeSolutionFact` selection and current-to-running refresh; media QML tests continue to own renderer/action behavior.
- Mail remains `passive.media.mail_panel` with authored `source_path`, provider-generated HTML, render-only inline WebEngine, and separate fullscreen behavior.

## Creation And Persistence Rules
- Blank insertion reads app preference `graphics.media_panel.source_input_exposed` from the `ShellWorkspacePresenter` explicitly bound to `GraphSceneBridge`; explicit connect forces Source exposed; OS paste/drop, frame capture, and trim Copy force it hidden. Media actions remain solely in `MediaPanelActionService`; no canvas aggregate exists.
- External paste and drop share `CanvasImportController` and `clipboard_paste_nodes.py`. Automatic selects Media Panel for supported media; Ask also offers applicable literal Text/Panel/path alternatives. Raw media chosen as Text or Panel stages a project copy and stores its exact managed reference. Native drop capture never transports image bytes through QML or bypasses existing drop targets.
- Project load, fragment paste, custom workflows, undo, and redo preserve serialized exposure exactly. Property overrides never imply exposure.
- The three pre-cutover media identities have no aliases or project migration. The frozen 133-row catalogue is historical; the structural overlay yields the 131-row current catalogue.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_media_panel.py tests/test_media_panel_creation_preferences.py tests/test_media_panel_source_resolution.py tests/test_media_video_state.py tests/test_media_panel_qml_surface.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py tests/test_video_trim.py tests/test_project_review_deck.py tests/test_pdf_preview_provider.py tests/test_preview_image_ids.py tests/test_passive_image_nodes.py --ignore=venv -q
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe -m pytest `
  "tests/test_shell_isolation_phase.py::test_shell_isolation_target[main_window__passive_image_nodes__editors_and_storage]" `
  "tests/test_shell_isolation_phase.py::test_shell_isolation_target[main_window__passive_image_nodes__crop_interactions]" `
  "tests/test_shell_isolation_phase.py::test_shell_isolation_target[main_window__passive_pdf_nodes__editors_and_storage]" `
  "tests/test_shell_isolation_phase.py::test_shell_isolation_target[main_window__passive_pdf_nodes__toolbar_and_page_resolution]" `
  --ignore=venv -q -n 0
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

## Breadcrumbs
- [Passive, Media, And Tabular Surfaces](../subsystems/passive_media_tabular_surfaces.md)
- [Viewer Session, Native Overlay, And Fullscreen](viewer_session_overlay_fullscreen.md)
- [Graphics Settings, Themes, And Preferences](graphics_settings_themes_preferences.md)
- [Clipboard, Undo, Redo, And Mutation History](clipboard_undo_redo_mutation_history.md)

## Update Triggers
Update when Media Panel ports/properties, effective-source states, exposure authority, creation overrides, renderer actions/lifecycle, fullscreen payloads, media integration actions, Mail separation, or focused tests change.
