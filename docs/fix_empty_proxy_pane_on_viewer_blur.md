## Fix Empty Proxy Pane On Viewer Blur

### Summary
The current blur path demotes a `focus_only` live viewer to `live_mode="proxy"` immediately, but the proxy image only appears after an async `materialize_viewer_data(..., export_formats=["png"])` round-trip. That leaves a visible gap where the proxy pane is active with no preview source. The fix is to capture a transient local preview from the live overlay before releasing it, surface that preview through the existing proxy-image path immediately, and keep the existing worker-side PNG materialization as the authoritative replacement.

### Implementation Changes
- In [`viewer_session_bridge.py`](C:\Users\emre_\PycharmProjects\EA_Node_Editor\ea_node_editor\ui_qml\viewer_session_bridge.py), add transient per-session proxy-preview state owned by the bridge.
  - Capture a preview before sending the `update_viewer_session(... live_mode="proxy")` command in `_apply_desired_live_mode`.
  - Save the captured image to a temp PNG owned by the bridge and synthesize it into `payload()["data_refs"]["preview"]` only when authoritative `png`/`preview` refs are absent.
  - Keep the existing `pending_proxy_snapshot_refresh` and materialization flow so the worker still produces the real stored PNG.
  - Clear temp preview files when an authoritative preview arrives, when the session closes/resets, when project projections are rebuilt, and when nodes are removed.

- In [`viewer_host_service.py`](C:\Users\emre_\PycharmProjects\EA_Node_Editor\ea_node_editor\ui_qml\viewer_host_service.py), add a non-slot helper that returns a `QImage` snapshot of the current overlay widget for a given `(workspace_id, node_id)`.
  - Prefer a binder-specific capture hook when available.
  - Fall back to widget framebuffer or `grab().toImage()` for non-DPF backends.
  - If capture fails, return an empty image so current behavior degrades safely to the existing async materialization path.

- In [`dpf_viewer_widget_binder.py`](C:\Users\emre_\PycharmProjects\EA_Node_Editor\ea_node_editor\ui_qml\dpf_viewer_widget_binder.py), add an optional `capture_preview_image(widget)` helper for the DPF backend.
  - Use `QtInteractor.screenshot(return_img=True)` to capture the exact current frame.
  - Convert the returned array to `QImage` and hand it back to `ViewerHostService`.
  - Do not change bind/release behavior or live transport handling.

### Interfaces
- No `.sfe`, execution protocol, or QML contract changes are required.
- Internal optional binder extension only:
  - `capture_preview_image(widget) -> QImage | None`
- `GraphViewerSurface.qml` can remain unchanged because it already prefers `data_refs.png` and falls back to `data_refs.preview`, and `LocalMediaPreviewImageProvider` already resolves absolute external paths.

### Test Plan
- Add a bridge unit test covering blur from `live_mode="full"` with no existing `png` ref:
  - blur captures a local preview immediately,
  - projected session payload exposes `data_refs.preview` before `viewer_data_materialized`,
  - async materialization is still requested.
- Add a bridge unit test that `viewer_data_materialized` with authoritative `png` replaces the transient preview and cleans up the temp file.
- Add cleanup tests for close/reset/project reload/node removal so transient preview files are not leaked.
- Add a host-service or binder test that DPF preview capture uses the live interactor path and returns a non-null image.
- Extend the QML viewer surface host test so a state with only `data_refs.preview` still shows the proxy image, not an empty pane.

### Assumptions
- Desired behavior is immediate frozen-frame proxy on blur, not waiting for worker materialization.
- The transient preview is session-local temp state only and should not be persisted, serialized, or used after restart.
- If capture fails on a backend, the existing async PNG materialization remains the fallback behavior.
