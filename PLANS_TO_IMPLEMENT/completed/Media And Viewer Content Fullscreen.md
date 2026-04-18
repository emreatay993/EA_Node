# Media And Viewer Content Fullscreen

## Summary
Add a transient in-app fullscreen overlay for media and DPF viewer nodes. The overlay is shell-owned, opened from node-surface controls or `F11`, closed with `Esc`, `F11`, or a close button, and keeps fullscreen state out of saved project data. Media renders through QML using the same source, crop, and fit semantics as the node preview; live viewer fullscreen reuses the existing native overlay host instead of creating a second viewer widget.

## Key Changes
- Add a shell-level `contentFullscreenBridge` and render a new `ContentFullscreenOverlay.qml` from [MainShell.qml](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/MainShell.qml).
- Add fullscreen affordances to media and viewer surfaces using `GraphSurfaceButton`, preserving `embeddedInteractiveRects` so node drag/selection does not steal clicks.
- Handle `F11` in the graph/canvas path: close if fullscreen is open, otherwise open the single selected eligible media/viewer node; show a graph hint if no eligible node is selected.
- Extend the viewer overlay host so the existing live viewer widget retargets to the fullscreen viewport while open, then returns to the node viewport on close.

## Public Interface Changes
- New QML context property `contentFullscreenBridge` with `open`, `node_id`, `workspace_id`, `content_kind`, `title`, `media_payload`, `viewer_payload`, `last_error`, and a `content_fullscreen_changed` signal.
- New bridge slots: `request_open_node(node_id) -> bool`, `request_toggle_for_node(node_id) -> bool`, `request_close()`, and `can_open_node(node_id) -> bool`.
- New viewer host/overlay contract: `ViewerHostService` and `EmbeddedViewerOverlayManager` accept an optional fullscreen target for one `(workspace_id, node_id)` and compute geometry from `objectName: "contentFullscreenViewerViewport"` when active.
- Add a `fullscreen` UI icon in [icon_registry.py](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui/icon_registry.py) and the shell icon folder; use it for node buttons and the overlay close/restore affordance.

## Execution Tasks

### T01 Fullscreen State Contract
- Goal: Create the shell-owned state and request API for opening/closing content fullscreen.
- Preconditions: Existing shell context bootstrap and graph scene bridge remain unchanged.
- Conservative write scope: `ea_node_editor/ui_qml/content_fullscreen_bridge.py`, shell composition/context binding, shell overlay state helpers, and focused bridge tests.
- Deliverables: Bridge state model, node eligibility checks for image/PDF/viewer nodes, media payload normalization using existing PDF preview/path semantics, and lifecycle cleanup on workspace switch or node deletion.
- Verification: Unit tests for eligible/ineligible nodes, missing media files, PDF preview payloads, close-on-workspace-switch, and one-active-fullscreen invariant.
- Non-goals: No saved-project schema changes, no OS fullscreen, no separate top-level window.
- Packetization notes: `P01`; this is the required contract packet before QML surfaces or viewer retargeting.

### T02 Shell Overlay And Media Renderer
- Goal: Add the in-app fullscreen overlay and media rendering path.
- Preconditions: `T01` bridge exposes stable media/viewer payloads.
- Conservative write scope: new `ContentFullscreenOverlay.qml`, [MainShell.qml](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/MainShell.qml), and small shared media geometry/helper reuse only if needed.
- Deliverables: Full-window dimmed overlay, focused top bar with title and `Esc / F11` hint, close button, media display for image/PDF, local fit modes `Fit`, `Fill`, and `100%`, and no editing/crop mutation in fullscreen.
- Verification: QML contract tests or shell runtime tests proving overlay visibility, focus capture, Escape close, media payload rendering states, and no background interaction while open.
- Non-goals: No PDF page editing, no crop editing, no new media file picker from fullscreen.
- Packetization notes: `P02`; can land after `T01` and before live viewer retargeting.

### T03 Surface Buttons And Shortcut
- Goal: Make fullscreen discoverable and keyboard-accessible.
- Preconditions: `T01` and `T02` are available.
- Conservative write scope: [GraphMediaPanelHeaderControls.qml](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml), [GraphMediaPanelPreviewViewport.qml](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewViewport.qml), [GraphViewerSurface.qml](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml), and [GraphCanvasInputLayers.qml](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml).
- Deliverables: Media viewport fullscreen button visible on hover/selection when preview is ready and crop mode is inactive; viewer toolbar fullscreen button replacing the inert `moreButton`; `F11` open/close behavior for a single selected eligible node.
- Verification: Surface contract tests for button visibility, click routing, interactive rect counts, crop-mode suppression, viewer toolbar rect updates, and `F11` no-op/hint behavior.
- Non-goals: No double-click gesture and no node context-menu entry in v1.
- Packetization notes: `P03`; depends on `T01`, can be implemented in parallel with `T04` after the bridge contract is stable.

### T04 Interactive Live Viewer Retargeting
- Goal: Make DPF viewer fullscreen interactive when a live session is available or can be opened.
- Preconditions: `T01` bridge state and `T02` overlay viewport object name exist.
- Conservative write scope: [viewer_host_service.py](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/viewer_host_service.py), [embedded_viewer_overlay_manager.py](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py), and viewer host tests.
- Deliverables: Fullscreen pin for the active viewer node, native widget geometry retargeting to the fullscreen viewport, proxy image/status while live is opening or blocked, and restoration to node viewport on close.
- Verification: Tests for retarget geometry, widget reuse rather than duplicate bind, close/restore behavior, workspace switch cleanup, blocked viewer fallback, and no live widget orphaning.
- Non-goals: No new viewer backend, no camera-control redesign, no automatic workflow rerun when viewer data is blocked.
- Packetization notes: `P04`; keep separate because it crosses QML/native widget ownership.

### T05 Regression Closeout
- Goal: Lock behavior across shell, media, and viewer paths.
- Preconditions: `T01` through `T04` complete.
- Conservative write scope: tests and any minimal docs/changelog note if the repo expects one.
- Deliverables: Targeted regression coverage, manual smoke checklist, and final review of shortcut conflicts.
- Verification: Run `.\venv\Scripts\python.exe -m pytest` for the touched graph-surface, shell bridge, viewer surface, viewer host service, and embedded overlay manager tests.
- Non-goals: No broad UI refactor or packet doc generation unless this plan is converted into a work-packet set.
- Packetization notes: `P05`; regression-only packet if packetized.

## Work Packet Conversion Map
1. `P00 Bootstrap`: create packet index/ledger/prompts only if this plan becomes a packet set.
2. `P01 Fullscreen State Contract`: derived from `T01`.
3. `P02 Shell Overlay And Media Renderer`: derived from `T02`.
4. `P03 Surface Buttons And Shortcut`: derived from `T03`.
5. `P04 Interactive Live Viewer Retargeting`: derived from `T04`.
6. `P05 Regression Closeout`: derived from `T05`.

## Test Plan
- Unit/contract: content bridge eligibility, media payload normalization, PDF preview payloads, overlay open/close lifecycle, and workspace/node deletion cleanup.
- QML surface: media button visibility and rects, viewer toolbar button routing, `F11` selection behavior, Escape close, and background interaction blocking.
- Viewer native host: fullscreen geometry retarget, widget reuse, proxy fallback, restore-on-close, and no orphaned overlay containers.
- Manual smoke: image node fullscreen, PDF node fullscreen, crop mode suppression, closed viewer proxy fullscreen, live DPF viewer interactive fullscreen, `Esc`/`F11` close, and workspace switch cleanup.

## Assumptions
- Chosen UX: in-app overlay, button plus `F11`, interactive live viewer support.
- Only one fullscreen content overlay is active at a time.
- Fullscreen state is transient UI state and is never serialized into `.sfe` project files.
- The node’s existing crop/page/source settings are viewed in fullscreen but not edited there.
- `F11` is content fullscreen, not OS/app-window fullscreen, for this feature.
