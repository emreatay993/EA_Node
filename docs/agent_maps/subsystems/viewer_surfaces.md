# Viewer Surfaces, Native Overlays, And Fullscreen

## Purpose
Use this for embedded viewer sessions, native overlay management, fullscreen content, viewer host services, and DPF viewer surfaces.

## Start Here
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/engineering_viewer_widget_binder.py`
- `ea_node_editor/ui_qml/plot_host_service.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `ea_node_editor/ui_qml/native_overlay_owners.py`
- `ea_node_editor/ui_qml/viewer_control_bridge.py`
- `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
- `ea_node_editor/ui_qml/ContentFullscreenOverlay.qml`
- `ea_node_editor/ui_qml/components/graph/viewer/`
- `ea_node_editor/ui_qml/components/graph/plot/`
- `ea_node_editor/execution/viewer_session_service.py`

## Do Not Start Here
- Passive media surfaces unless the content is non-execution media.
- DPF node definitions before viewer transport/session ownership is clear.

## Common Changes
- Keep viewer session backend, bridge, overlay manager, and fullscreen bridge aligned.
- Keep worker session projection authoritative in `_ViewerSessionProjection`; optimistic command phase/options/playback/error belong to `_ViewerPendingDisplay` and are replaced by the next authoritative event. Normalize events once on ingress rather than rebuilding execution models from QML reads.
- Inject the viewer camera-capture callable at runtime composition with a late-bound host-service reference; preview capture/cache stays owned by `ViewerHostService` and does not pass through the session bridge.
- `EmbeddedViewerOverlayManager.export_overlay_snapshots()` is the native-overlay export handoff: it returns visible geometry-ready overlays in canvas-relative coordinates with an owner string. Keep owner ids centralized in `native_overlay_owners.py`; unknown visible native overlays should fail export rather than disappear silently.
- Native inline viewer overlays short-circuit polish/geometry/move/resize work and disable QWidget updates while `GraphCanvas.nativeOverlaySuppressionActive` is true. Inline live mode begins only after a proxy-viewport double-click; selection, hover, and single-click remain proxy. `ViewerHostService` owns one attached-but-hidden retained-inline slot only for a widget previously created by explicit inline activation, while fullscreen/detached use explicit presentation holds. Unchanged session/transport reactivation skips the binder; selection/background loss demotes, and identity or lifecycle termination still calls the release path.
- `PlotHostService` owns live widget retargeting for embedded, fullscreen, and detached presentations.
- Plot live overlays use the overlay manager's `plot_host` owner so plot syncs do not remove default viewer overlays.
- Inline plot previews use an in-memory raster preview cache: capture the real native widget frame as a copied `QImage` on embedded live-exit, serve it through `image://plot-preview-cache/...`, and invalidate it on render-signature changes. Live-exit has the same mirror boundary as the DPF viewer: `PlotHostService` captures the exit raster, then defers the overlay release (and with it the native hide) until QML confirms the swapped image via `notify_cached_preview_swapped(node_id, source)` and one `afterRendering` frame has passed (`_EMBEDDED_EXIT_DEMOTION_TIMEOUT_MS` fallback), so the reveal never repaints a stale proxy frame; a pending exit keeps the overlay hosted through queued syncs, and re-activation cancels the demotion with the live overlay still bound.
- Inline plot live reactivation should restore transient backend view state from the same live-exit point: pyqtgraph view ranges and fixed axis layout for 2D plots, and PyVista camera state for 3D plots.
- Inline plot live activation should gate by actual on-screen viewport size (`graphNodeViewerViewport` dimensions multiplied by canvas zoom) only when `plot_surface.live_backend_id` resolves to pyqtgraph. Non-pyqtgraph live plotters and DPF viewer surfaces rely on backend/session readiness plus overlay geometry rather than the pyqtgraph clipping workaround.
- Keep cached/proxy plot content visible through live handoff until the native overlay reports attached and exact-viewport geometry-ready; `liveSurfaceActive` is the request, while `liveOverlayReady` is the visual handoff boundary. Plot overlays should use the mapped `graphNodeViewerViewport` rect, normalize cached preview rasters to overlay size/DPR, and avoid broader body fallback geometry.
- Plot live/cache QML should depend on `PlotHostService.plot_overlay_revision`, not just active overlay count, because switching directly between two plot overlays can keep the count unchanged while readiness and identity change. While any fullscreen content is open, non-fullscreen inline plot overlays and inline cached plot images should be suppressed; plot fullscreen changes should publish only the fullscreen target before the queued retarget sync so old native content cannot flash in the fullscreen viewport. Keep the fullscreen scrim opaque so graph cached previews cannot show through while native fullscreen content attaches.
- Plot fullscreen target selection should be keyed from the open fullscreen bridge node identity, not from optional `native_overlay` payload metadata. A plot live overlay that is the fullscreen target must wait hidden until `contentFullscreenViewerViewport` is visible and sized; do not show it at the inline `graphNodeViewerViewport` fallback geometry.
- Plot cached-preview provider URLs must preserve exact workspace/node IDs without double-decoding percent-encoded text, or distinct node IDs can collide at image-provider request time.
- During canvas viewport interaction or node drag, inline plot surfaces should leave the native live overlay and show the cached raster preview until interaction settles; wheel-zoom eligibility is mirrored in GraphCanvasViewportController.qml and `graph_canvas_state/`.
- Fullscreen PDF uses QML `PdfMultiPageView` in `ContentFullscreenOverlay.qml` and owns reader controls there: text search, match navigation, zoom, fit page/width/actual size, rotate, and page shortcuts. Keep this QML path separate from Python bridge fallback clamping.
- Plot session windows are deprecated and disabled; keep inline plot live previews on the embedded path.
- Finalize PyVista/QVTK plot widgets before hiding or detaching their Qt containers so VTK does not clean up against an invalid native OpenGL handle.
- DPF viewer surfaces follow the embedded live-preview pattern from plot surfaces: QML calls `ViewerHostService.set_embedded_interaction_active(node_id, active)`, keeps an in-memory `image://viewer-preview-cache/...` raster visible during live-overlay handoff, and uses `viewer_overlay_revision`/`embedded_live_overlay_ready(node_id)` as the visual readiness boundary. Live-exit has the mirror boundary: the host service captures the exit preview, then defers the session-bridge demotion (and with it the overlay hide) until QML confirms the swapped image via `notify_cached_preview_swapped(node_id, source)` and one `afterRendering` frame has passed (`_EMBEDDED_EXIT_DEMOTION_TIMEOUT_MS` fallback), so the reveal never repaints a stale proxy frame. Re-activation during the pending exit cancels the demotion and keeps the live overlay bound. They are not gated by the pyqtgraph plot screen-size threshold. `GraphViewerSurfaceBody.qml` must invoke that slot only via its coalesced `Qt.callLater` queue (`_queueEmbeddedInteractionSync`) from property-change handlers: the slot re-emits `ViewerSessionBridge.sessions_changed`, and a direct call from the `embeddedInteractionActive` change handler runs inside the `bridgeSessionProjectionSeed` binding update and logs a QML binding loop (`test_session_projection_seed_survives_synchronous_state_flip_without_binding_loop`).
- Neutral CAD/FE scenes use the same host/overlay/fullscreen ownership through
  `corex_scene`. The binder keeps one PyVista widget, reuses datasets and actors
  for same-session/revision view changes, applies display-only overlay unit
  scaling, and exposes layer visibility/isolate plus picked-cell snapshots.
  Native OCP stays worker-local: only bounded, hashed VTK XML bytes cross in
  shared memory, and the binder deep-copies the reconstructed dataset before
  closing the attachment. File-backed assets remain the fallback. Do not add a
  second engineering overlay manager or route live OCP/VTK objects into QML.
- Engineering fullscreen and detached presentations reuse
  `ViewerQuickControls.qml` and `ViewerSidePanel.qml`. `ViewerControlBridge`
  owns node-scoped options, bookmarks, selections, query, and export;
  `ContentFullscreenBridge` does not own viewer commands.
- `ViewerHostService` reparents one live native viewer across inline, detached,
  and fullscreen targets with `fullscreen > detached > inline` priority. A
  detached-window close docks inline, fullscreen temporarily takes ownership,
  and reset/session/workspace/node/backend loss closes transient presentations.
- DPF viewer QML must retain the last non-empty viewer-preview-cache image source while a same-node cached frame remains valid, including during node selection and drag demotion. Clear it only for real invalidation such as node change, fullscreen takeover, run-required state, closed session, or a missing cache source.
- DPF viewer cached previews and transient camera/view state are in-memory only. Do not reintroduce temp PNG preview materialization, project persistence, or `materialize_viewer_data(... export_formats=["png"])` for embedded demotion.
- `ViewerHostService` keys the cached camera/view state by a camera-relevant signature (session, backend, transport revision, transport, data_refs) on both capture and restore, so the camera survives option-only and playback changes and resets only when the transported geometry changes; preview-signature changes migrate the camera entry instead of clearing it.
- `DpfViewerWidgetBinder` owns PyVista camera capture/restore for live viewer reactivation (including a same-session re-populate snapshot when the bind request carries no camera payload); release QVTK widgets while they are still attached before hiding or detaching containers. It also computes component-aware post-warp display stats served through `ViewerHostService.viewer_render_stats(node_id)` alongside `apply_standard_view`/`reset_overlay_camera`/`camera_state_snapshot`/`apply_overlay_camera_state`/`export_viewer_screenshot`, and installs the fullscreen shortcut event filter on the fullscreen-target widget.
- For cross-process viewer work, update execution viewer protocol tests.
- `ViewerSessionBridge` advances epochs itself only for true project/reset/global run-required paths; run-driven invalidation has one path, `adopt_committed_invalidation(...)`, which adopts the independently committed high-level projection snapshot without incrementing again. It does not subscribe to `ShellWindow.execution_event`: the sole queued shell intake calls `handle_viewer_execution_event(...)` directly once after run-state routing. That consumer retains the existing node-settled, viewer-event, epoch, session, and request filters. Concrete transport responses reach it only after local client validation and translation to those projection epochs. It retires matching pending queries/presentation holds/inline activation and rejects old-epoch or mismatched-request responses before signals or session mutation. Unaffected viewer projections remain unchanged; the bridge never resets `ViewerHostService` for an ordinary run.
- Keep native overlay and QML surface tests separate from generic graph node tests.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_control_bridge.py tests/test_viewer_host_service.py tests/test_viewer_preview_cache_provider.py tests/test_embedded_viewer_overlay_manager.py tests/test_viewer_surface_contract.py tests/test_viewer_surface_host.py --ignore=venv -q
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_plot_preview_cache_provider.py tests/test_plot_host_service.py tests/test_plot_fullscreen_overlay.py --ignore=venv -q; $exitCode = $LASTEXITCODE; Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue; exit $exitCode
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_plot_detached_window.py --ignore=venv -q; $exitCode = $LASTEXITCODE; Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue; exit $exitCode
```

## Breadcrumbs
- [Viewer Session, Native Overlay, And Fullscreen](../feature_routes/viewer_session_overlay_fullscreen.md)
- [Ansys DPF Operator Nodes, Viewer, And Transport](../feature_routes/ansys_dpf_operator_viewer_transport.md)
- [Neutral CAD/FE Engineering Viewer](../feature_routes/neutral_cad_fe_engineering_viewer.md)

## Update Triggers
Update when viewer session protocol, viewer-control ownership, engineering
viewer shared-memory binding, plot/viewer host services, inline
preview/view-state cache behavior, plot or viewer detached-window lifecycle,
overlay manager geometry/export snapshots, fullscreen bridge, or
viewer/native-overlay tests change.

## 2026-07-11 Performance Ownership

- Viewer/plot bridge identities remain stable while worker pools and binders allocate once on first use. Fullscreen content uses a retained loader and preserves overlay identity, geometry, focus, close, and restore behavior.
