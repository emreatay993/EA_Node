# Floating Hover Toolbar for Graph Nodes

> Visual reference: [`node_overlay_button_variants.html`](../../node_overlay_button_variants.html) — **Variant 1: Floating top toolbar** is the target design. Smart flip (below when near top edge) is required per user request.

## Context

Node-level actions are currently scattered and inconsistent across node types:

- **Common actions** (duplicate, delete, rename) live only in the right-click context menu — low discoverability.
- **Viewer nodes** (`GraphViewerSurface.qml` lines 1115–1297) render 5 always-visible inline buttons: Open session, Play/Pause, Step, Keep Live, Fullscreen.
- **Media nodes** (`GraphMediaPanelHeaderControls.qml` lines 43–121) render 3 always-visible inline buttons: Crop, Fullscreen, Repair.
- **Scope-entry OPEN badge** (`GraphNodeHeaderLayer.qml` lines 365–410) is always visible even when unused.

In dense graphs this creates visual noise and takes vertical space that could be used for content. The user picked Variant 1 from the variants document: a floating toolbar that slides in above the node on hover-or-selection, with smart flip to below when near the top viewport edge. Per-node-type actions merge into the same toolbar so the UX is unified.

## Outcome

- One floating toolbar per node, showing both common actions and type-specific actions for that node.
- Visible when the node is hovered OR selected; hidden otherwise.
- Positioned above the node by default; flips below when the node is too close to the viewport top.
- Respects each node's theme color (nodes can have individual theme colors — toolbar accent tracks that color, background stays neutral dark chrome).
- HALTED and OPEN **badges remain in the title band** as passive state indicators; the toolbar adds an explicit "Enter scope" action button that shares the same `nodeOpenRequested` wiring when `canEnterScope` is true.
- Inline per-type buttons are removed from node bodies — bodies become pure content.

## Key Changes

1. **Action provider contract.** New `availableActions` array on `GraphNodeHost` built from: (a) common actions computed by the host, (b) type-specific actions published by the loaded surface via a new `surfaceActions` property. Each action is a structured record: `{ id, label, icon, kind, enabled, primary }` where `kind` is `common | viewer | media | custom`.
2. **Unified action signal.** New signal `nodeActionRequested(nodeId, actionId, payload)` on `GraphNodeHost`, routed through `GraphSceneBridge` to the existing Python handlers. Replaces the per-surface bespoke signals (`requestSessionToggle`, `requestPlayPause`, `triggerHoverAction`, etc.).
3. **New canvas overlay layer.** A single `GraphNodeOverlayToolbarLayer.qml` mounted once at canvas scope, above the nodes repeater but inside the world transform (so it pans/zooms with the graph). It hosts at most one visible toolbar at a time — the one belonging to the currently hovered-or-selected node. This mirrors the existing `GraphSearchOverlay.qml` / `ConnectionQuickInsertOverlay.qml` single-instance overlay pattern.
4. **Floating toolbar component.** New `GraphNodeFloatingToolbar.qml` rendering the pill-shaped toolbar from Variant 1: horizontal row of `GraphSurfaceButton` instances, 4 px gap, 4 px internal padding, chrome matching `GraphNodeChromeBackground` (dark surface + node-theme border), subtle drop shadow, slide-in animation (180 ms cubic-bezier(0.2, 0.8, 0.2, 1)).
5. **Smart flip positioner.** New helper `ea_node_editor/ui_qml/components/graph/toolbar_positioning.js` computing toolbar anchor as a function of node scene-rect, toolbar size, and canvas viewport rect. Prefers above; flips below when `nodeTopY - toolbarHeight - gap < viewportTopY + safetyMargin`. Also handles horizontal centering with left/right flip when near horizontal edges.
6. **Hover-or-selected trigger.** New property `host.toolbarActive = cardHoverHandler.hovered || isSelected` with a 120 ms grace period (QTimer-backed) before hiding, so the mouse can travel from node into the toolbar without losing it. Re-uses existing `cardHoverHandler` in `GraphNodeHost.qml` line 579.
7. **Theme color respect.** New `host.nodeThemeColor` property derived from the node model's category/user-set theme. Toolbar primary-action accent and hover border are tinted with this color; neutral background stays dark. Reused color resolver — no new theme plumbing.
8. **Inline button removal.** Delete the inline button blocks from `GraphViewerSurface.qml` (lines 1115–1297) and `GraphMediaPanelHeaderControls.qml` (lines 43–121). Their handlers become handlers for the new `nodeActionRequested` action ids. The HALTED badge and OPEN badge in the title band stay.
9. **Metrics contract extension.** Add `FloatingToolbarMetrics` dataclass to `ea_node_editor/ui_qml/graph_geometry/surface_contract.py` (toolbar_height, button_size, button_gap, internal_padding, gap_from_node, safety_margin). Compute in `standard_metrics.py` and `viewer_metrics.py`. Expose via the existing metrics payload so QML can read via context property.
10. **Keyboard parity.** Toolbar buttons receive keyboard focus when the node is selected. Tab cycles; Enter activates. Ensures accessibility parity with the removed inline buttons.

## Design Decisions

- **Single overlay instance at canvas level**, not one toolbar per node. A Repeater would mount N toolbars for N nodes but only one is ever visible — the single-instance pattern saves Items and avoids z-order fights.
- **Overlay lives inside the world transform**, so the toolbar pans and zooms with the node. This matches user expectation (the toolbar feels "attached" to the node) and is consistent with `GraphSearchOverlay`.
- **Common actions come from `GraphNodeHost`, type-specific from the surface.** Keeps per-type knowledge inside the surface component without a central registry. The host concatenates and hands the combined list to the toolbar overlay.
- **OPEN badge kept, plus a toolbar "Enter scope" button.** Badge = state ("this node has a scope you can enter"). Toolbar button = action ("enter it now"). Both call `_requestScopeOpen()` in `GraphNodeHeaderLayer.qml` — no duplicate logic.
- **Neutral chrome + theme accent.** No state-tinting (no running-green / failed-red toolbar backgrounds). Running/failed state is already communicated by the node halo and HALTED badge.

## Critical Files

**New files:**
- `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeOverlayToolbarLayer.qml` — single-instance overlay host.
- `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeFloatingToolbar.qml` — the toolbar component.
- `ea_node_editor/ui_qml/components/graph/overlay/toolbar_positioning.js` — smart-flip geometry helper.
- `ea_node_editor/ui_qml/graph_geometry/floating_toolbar_metrics.py` — `FloatingToolbarMetrics` dataclass.

**Modified files:**
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml` — add `availableActions`, `nodeThemeColor`, `toolbarActive`, `nodeActionRequested` signal, grace-period timer (reuses `cardHoverHandler` at line 579).
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml` — mount the new overlay layer above node layer, inside world transform.
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml` — delete inline buttons (lines 1115–1297); publish `surfaceActions` list; re-route handlers to the new action dispatcher.
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml` — delete button rows (lines 43–121); publish `surfaceActions` via parent surface; crop Apply/Cancel stay inside the crop overlay (they're modal, not toolbar).
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml` — expose `surfaceActions`, keep crop overlay as-is.
- `ea_node_editor/ui_qml/graph_geometry/surface_contract.py` — add toolbar metrics to `GraphNodeSurfaceMetrics` payload.
- `ea_node_editor/ui_qml/graph_geometry/standard_metrics.py` and `viewer_metrics.py` — compute and emit toolbar metrics.
- `ea_node_editor/ui_qml/graph_scene_bridge.py` (or wherever node action plumbing lives) — handle `nodeActionRequested(nodeId, actionId, payload)` → existing Python dispatch for duplicate/delete/rename; viewer actions routed to `viewerSessionBridgeRef`; media actions routed to the media surface service.

**Reused components (no new button styling):**
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceButton.qml` — the toolbar uses this as-is with its existing `controlStarted`, hover, and theme props.

## Execution Tasks

### T01 — Action provider contract + metrics

- Add `FloatingToolbarMetrics` dataclass; wire into `GraphNodeSurfaceMetrics.to_payload()`.
- Add `availableActions`, `nodeThemeColor`, `toolbarActive` properties and `nodeActionRequested(nodeId, actionId, payload)` signal on `GraphNodeHost`.
- Implement the 120 ms hover-grace timer using `cardHoverHandler.hovered || isSelected` as the truth source.
- **Preconditions:** none.
- **Deliverables:** host exposes action list and signal; metrics payload includes toolbar fields; nothing renders yet.

### T02 — Overlay layer + floating toolbar component + smart flip

- Create `GraphNodeOverlayToolbarLayer.qml` and mount it in `GraphCanvasRootLayers.qml` above the nodes repeater, inside the world transform.
- Create `GraphNodeFloatingToolbar.qml` (Variant 1 visual: horizontal pill, dark chrome, theme-tinted border, slide-in animation, 180 ms easing).
- Create `toolbar_positioning.js` with `computeAnchor(nodeRect, toolbarSize, viewportRect, metrics) → {x, y, flipped}` — prefers top-anchor, flips to bottom when `nodeTopY - toolbarHeight - gap < viewportTopY + safetyMargin`.
- Wire overlay to track the current "active" node (hovered or selected). When multiple nodes are simultaneously selected, prefer the hovered one; else the most-recently-selected one.
- **Preconditions:** T01.
- **Deliverables:** toolbar renders above nodes for common actions only (duplicate / delete / rename / enter-scope). Smart flip demonstrable by scrolling the canvas so a node touches the top edge.

### T03 — Viewer surface action migration

- Remove inline button block from `GraphViewerSurface.qml` (lines 1115–1297).
- Publish `surfaceActions` list from the viewer surface: `openSession`, `playPause`, `step`, `keepLive`, `fullscreen` with `enabled` / `primary` flags derived from the current session state.
- Route those action ids in `nodeActionRequested` handler → `viewerSessionBridgeRef` methods (existing).
- Keep the viewer mode badge (lines 1381–1404) inside the surface — it's a status indicator, not an action.
- **Preconditions:** T02.
- **Deliverables:** viewer-node toolbar shows all five viewer actions alongside common actions; viewer body is pure content.

### T04 — Media surface action migration

- Remove button rows from `GraphMediaPanelHeaderControls.qml` (lines 43–121).
- Publish `surfaceActions` from `GraphMediaPanelSurface.qml`: `crop`, `fullscreen`, `repair` (repair enabled only when file missing).
- Crop Apply/Cancel (lines 707–733 of `GraphMediaPanelSurface.qml`) **stay inside the crop overlay** — they're modal controls for an active operation, not node actions.
- The "Missing file" badge (lines 123–152) stays as a status indicator in the header.
- **Preconditions:** T02.
- **Deliverables:** media-node toolbar shows crop / fullscreen / repair alongside common actions; media header band only shows the status badge.

### T05 — Tests and polish

- Extend `tests/test_viewer_surface_contract.py` to assert that `GraphNodeSurfaceMetrics.to_payload()` now contains the `floating_toolbar` block and that `GraphViewerSurface` no longer exports inline button rects (removed controls should not appear in `embeddedInteractiveRects`).
- Extend `tests/test_graph_surface_input_controls.py` with a probe QML that mounts `GraphNodeFloatingToolbar` and asserts: (a) toolbar rect is published, (b) clicking each action emits `nodeActionRequested(nodeId, actionId, …)` exactly once, (c) keyboard Tab/Enter parity, (d) external-hover prop keeps the toolbar visible during mouse travel from node to toolbar.
- Add new `tests/test_floating_toolbar_positioning.py` — pure-Python unit tests for `computeAnchor` via a Python port of the JS helper, OR (preferred) use the existing offscreen-QML subprocess pattern to assert: toolbar above when node is mid-canvas, toolbar below when node is near viewport top, horizontal clamp when node is near left/right edges.
- Extend `tests/test_viewer_surface_host.py` to assert viewer surface no longer renders inline buttons and that its `surfaceActions` list has the expected 5 entries in the expected order.
- Manual smoke pass: hover a node → toolbar slides in above; select a different node while hovering → toolbar switches to the selected node; pan canvas so a node touches the top → toolbar flips below; change node theme color → toolbar border accent updates.
- **Preconditions:** T03, T04.
- **Deliverables:** CI green; visual checklist passes.

## Verification

**Automated (per `CLAUDE.md`, run with `pytest -n auto`):**

- `pytest -n auto tests/test_viewer_surface_contract.py tests/test_graph_surface_input_controls.py tests/test_viewer_surface_host.py tests/test_floating_toolbar_positioning.py`
- Full suite before finish: `pytest -n auto`

**Manual smoke (run the app):**

1. Hover a plain node → floating toolbar slides in above the node with Duplicate / Delete / Rename (and Enter scope if applicable).
2. Move mouse off the node onto the toolbar → toolbar stays (120 ms grace).
3. Select the node (click) → toolbar stays even without hover.
4. Drag a node to the very top of the viewport → toolbar flips to render below it.
5. Hover a viewer node → toolbar shows 5 viewer actions + common actions, inline buttons are gone from the node body.
6. Hover a media node with a missing file → toolbar shows Repair enabled; status badge stays in the title band.
7. Change a node's theme color → toolbar border accent updates to match on next hover.
8. Right-click context menu still offers Duplicate / Delete (redundancy is fine; both paths invoke the same dispatcher).

## Non-goals

- No change to the right-click context menu — it stays as the keyboard/power-user path.
- No state-tinted toolbars (running-green, failed-red). Node state stays communicated by the halo and HALTED badge.
- No new action beyond what currently exists somewhere in the UI, except the unified dispatcher signal.
- No work on property-editor embedded buttons (browse path, pick color, apply textarea). Those are bound to specific property rows in the node body and do not move to the toolbar.
- No redesign of the crop Apply/Cancel UX — they stay inside the crop overlay because they are modal.

## Risks and mitigations

- **Z-order bleed past neighboring nodes.** Mitigation: overlay is canvas-level (above the nodes repeater), not a node child.
- **Smart flip jitter when node is exactly on the threshold.** Mitigation: 8 px hysteresis in `computeAnchor` — once flipped, stay flipped until the node has 16 px clearance.
- **Action handler drift vs the existing procedural APIs** (`viewerSessionBridgeRef.play`, etc.). Mitigation: the new dispatcher routes to the same procedural APIs — no handler code is rewritten, only the entry point changes.
- **Keyboard parity regression.** Mitigation: T05 covers keyboard tests; if the probe can't assert focus, include in the manual smoke list with an explicit checkbox.
