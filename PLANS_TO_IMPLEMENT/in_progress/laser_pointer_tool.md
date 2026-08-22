# Laser Pointer Tool (Dot + Neon Line) for the Graph Canvas

> **Behavioral reference (source of truth):** the standalone, signed-off prototype
> [`mockups/laser_pointer_notetaking_prototype.py`](../../mockups/laser_pointer_notetaking_prototype.py).
> It is a single-file PyQt6/QML app (run `python mockups/laser_pointer_notetaking_prototype.py`; offscreen
> load check `python mockups/laser_pointer_notetaking_prototype.py --selftest`). The production overlay must
> **reproduce its function/state model and timing exactly** — `beginStroke / feed /
> finishStroke(ctrl) / onCtrlReleased / clear`, the `strokes[]` + `accumulating` + `ctrlDown`
> state, the min-distance point filter, the `PathMultiline` rendering, and the whole-stroke
> fade-on-release. All timing/visual values below were dialed in and locked in that prototype.

## Context

The editor has no way for a presenter to point at things during a walkthrough. We want a
**laser pointer** tool modeled on a benchmark whiteboard (analyzed frame-by-frame): a red **neon
trail** that follows hold-and-drag, plus a simpler **dot** mode. It is a transient presentation
aid — **ephemeral** (never written to the document model, no undo, not part of persistence) — but
its tuning values are **app-persistent settings** the user can adjust later.

**This laser pointer is the first tool of a new "stylus" toolbar** planned for the node editor.
The Laser toolbar button and its Dot/Line popover are the initial entry point and are expected to
**fold into that stylus toolbar** as more pen/annotation tools are added, rather than remaining a
standalone shell button long-term. Keep the laser's tool-state, bridge relay, and popover idiom
general enough that the stylus toolbar can host this and sibling tools without rework.

The critical, non-obvious behavior (verified against the video): the trail is **not** a comet/tail
that ages out point-by-point. The whole stroke holds full opacity while drawn and then
**dissolves uniformly as one unit when released/idle**. A naive per-point-lifetime implementation
is wrong. The prototype proved the right model and also proved the renderer choice: a `Canvas` +
`shadowBlur` glow is too slow (software blur over the whole growing path each frame → lag → Qt
coalesces mouse moves → jagged), whereas **GPU `QtQuick.Shapes`** is smooth at the project's
Qt 6.10.

The canvas is PyQt6 + Qt Quick. The overlay mounts into the existing layered QML scene; input is
QML-side; the toolbar button lives in the shell; the tuning values flow through the existing
graphics-settings persistence + bridge machinery.

## Outcome

- A **Laser** toolbar button opens a small **"Laser Pointer"** popover with **Dot** and **Line**
  modes (selected mode highlighted). Activating sets a modal laser state.
- **Dot mode:** a constant-size glowing red dot (radial gradient core → soft halo) follows the
  cursor 1:1; no trail. OS cursor hidden (`BlankCursor`).
- **Line mode (hold-to-draw):** hold **left button** and drag to lay a red **neon** stroke
  (white-hot core + saturated red + soft GPU-blurred glow, round caps/joins). The stroke stays
  fully lit while held (even if paused); on **release** it waits `idle_ms` then **dissolves
  uniformly** over `fade_ms`, then clears. Cursor is a crosshair.
- **Ctrl-to-pin:** while **Ctrl is held**, each left-drag lays a **separate, non-fading** line, so
  multiple **discontinuous** lines accumulate. **Releasing Ctrl dissolves them all together**
  (same graceful fade). **Esc** clears immediately. Switching tools / deactivating clears.
- Trail lives in **viewport/screen space**: constant size regardless of zoom, follows the live
  cursor, renders above everything (z above all canvas overlays).
- **Seven numeric tuning values are persistent, user-editable "advanced" settings** in the
  Graphics Settings dialog; the four behavior toggles + Ctrl-pin + coordinate space are
  **hardcoded** (not user-facing).
- Laser input never creates/selects nodes or edges; never mutates the document; not broadcast.

## Locked behaviors and values (from prototype sign-off)

**Behaviors (hardcoded, not exposed):** viewport/screen space · hold-to-draw · fade-on-release ·
GPU `Shapes` + `CurveRenderer` · soft glow via `MultiEffect` (auto-degrades under canvas perf
modes) · Ctrl-to-pin with dissolve-all-on-Ctrl-release · Esc clears.

**Values (defaults; the seven are user-exposed & persistent):**

| key | default | type | dialog range (suggested) | meaning |
|------|---------|------|--------------------------|---------|
| `fade_ms` | **760** | int | 80–1500 | uniform dissolve duration |
| `idle_ms` | **110** | int | 0–800 | grace after release before fade starts |
| `min_px` | **0.5** | float | 0–8 (0.5 step) | min distance between captured points |
| `core_w` | **2.5** | float | 0.5–8 (0.5 step) | white-hot core stroke width |
| `red_w` | **12** | float | 2–20 (0.5 step) | saturated red body width |
| `glow` | **23** | int | 0–60 | inner-halo width / glow strength |
| `dot_r` | **4** | int | 3–24 | dot core radius |

Fixed colors: laser `#ff2a2a`, core `#fff2f2`. Internal caps (not settings): `maxPoints` ≈ 400
per stroke (ring-trim), `maxStrokes` ≈ 60 (pinned cap).

## Key Changes

1. **New QML overlay** `GraphLaserPointerOverlay.qml` — top-most, viewport-space, renders the dot
   and a list of polylines (`strokes`) via `QtQuick.Shapes` `PathMultiline`, with whole-stroke
   uniform fade as a single `opacity` animation. Mirrors the prototype's render + fade logic.
2. **Mount** the overlay as the last child of `GraphCanvasRootLayers.qml` (z:1200), bound to laser
   state and to the persistent tuning properties.
3. **Interaction state** — add `laserModeActive`, `laserMode` ("dot"|"line"), `laserAccumulating`
   to `GraphCanvasInteractionState.qml`, with `setLaserActive/Mode/toggleLaser`.
4. **Canvas wrappers + cursor** — expose aliases/wrappers on `GraphCanvas.qml`; on activation set
   cursor (`Qt.BlankCursor` for dot, `Qt.CrossCursor` for line) via the existing
   `setNodeSurfaceCursorShape` / `clearNodeSurfaceCursorShape` (no new Python); `forceActiveFocus()`.
5. **Top-most capture layer** in `GraphCanvasInputLayers.qml` — a `MouseArea` enabled only in laser
   mode that feeds hold-drag points to the overlay QML-side (no per-move Python hop) and swallows
   all buttons so node/edge/marquee/pan never fire.
6. **Keys** — Ctrl press/release tracking (Ctrl-release → dissolve pinned lines) and Esc → clear,
   extending the existing `Keys.onEscapePressed`.
7. **Toolbar button + popover** in `ShellRunToolbar.qml` — a `ShellButton` opening a Dot/Line
   popover reusing the `GraphNodeFloatingToolbar.qml` inline-popover idiom + `GraphSurfaceButton`
   active styling; checked-state from a bridge `laser_active` property.
8. **Bridge relay** — `laser_active` (pyqtProperty+notify), `set_laser_active(bool)`,
   `set_laser_mode(str)` on `GraphCanvasStateBridge` / `graph_canvas_command_bridge.py`, forwarding
   to the active canvas.
9. **Persistent settings** — a `"laser"` block in `DEFAULT_GRAPHICS_SETTINGS` (`settings.py`) with
   MIN/MAX constants + defaults = the locked values; `normalize_laser_settings()` in
   `app_preferences.py`; a **"Laser Pointer (Advanced)"** group in `graphics_settings_dialog.py`;
   live `graphics_laser_*` pyqtProperties on `GraphCanvasStateBridge` (notify
   `graphics_preferences_changed`). The overlay binds these for live updates.

## Design Decisions

- **Viewport/screen space, not scene space.** A laser points at the screen: constant size at any
  zoom, follows the live cursor, no pan lag. The sub-second life makes mid-stroke pan/zoom a
  non-issue. (Scene-pinned alternative documented under Risks — rejected as default.)
- **Whole-stroke uniform fade = one `opacity` on a wrapper Item**, full color underneath. Driven by
  an idle `Timer(idle_ms)` started on **release** (not per move, since fade-on-release is locked) →
  a `NumberAnimation` opacity→0 over `fade_ms` → clear. This is *not* per-point aging.
- **GPU `QtQuick.Shapes` + `CurveRenderer`**, mirroring `EdgeRetainedLayer.qml`'s `Shape`/`ShapePath`
  idiom. **`PathMultiline`** renders multiple discontinuous pinned strokes in one `ShapePath`. Soft
  glow via `layer.effect: MultiEffect{blur}`. Reject `Canvas`/`shadowBlur` (proven laggy) and
  `QQuickPaintedItem` (per-frame Python; breaks 60fps + house pure-QML style).
- **Active vs pinned split (perf):** render **pinned** strokes in one Shape rebuilt only on
  pin/clear, and the **active** stroke in a separate Shape rebuilt per move. Avoids re-tessellating
  all pinned strokes on every `feed`.
- **Hold-to-draw** (not hover-follow): bare hover shows only the dot; trail draws on left-drag.
  Chosen by the user to avoid accidental trails.
- **Ctrl-release dissolves all pinned lines** (confirmed). Alternative (keep-until-Esc) noted in
  Open Questions but not the chosen behavior.
- **State QML-side, not Python.** The trail is ephemeral and updates at 60fps; a Python hop per
  mouse move would stutter. Only the mode/active toggle and persistent tuning cross the bridge.
- **Seven numeric values persistent; behaviors hardcoded.** Per user: slider-based settings are
  exposable in Graphics Settings; the on/off behaviors are locked.

## Critical Files

**New files:**
- `ea_node_editor/ui_qml/components/graph/overlay/GraphLaserPointerOverlay.qml` — the overlay
  (dot + neon multi-stroke trail + uniform fade). Port the prototype's QML logic.

**Modified — QML scene/input:**
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml` — import is already
  aliased `GraphOverlay` (line 3); mount the overlay as the **last child** (after
  `GraphCanvasMinimapOverlay`), `anchors.fill: parent`, **z:1200**; add a `pushLaser…` forwarder.
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml` — add
  `laserModeActive` / `laserMode` / `laserAccumulating` + `setLaserActive/Mode/toggleLaser`
  (close context menus + cancel pending wire drag on activate).
- `ea_node_editor/ui_qml/components/GraphCanvas.qml` — aliases + wrapper funcs (alias block
  ~lines 300–317; wrappers ~581–586); `pushLaser…` → `rootLayers`; `onLaserModeActiveChanged`
  cursor wiring via `setNodeSurfaceCursorShape`/`clearNodeSurfaceCursorShape` (wrappers exist
  ~lines 410–411) + `forceActiveFocus()`.
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml` — add top-most
  `MouseArea` `graphCanvasLaserCaptureArea` (peer of `panArea` ~lines 454–514; enabled only in
  laser mode, no open menus; `acceptedButtons: Qt.AllButtons`; `hoverEnabled`); Ctrl press/release
  tracking; extend `Keys.onEscapePressed` (~lines 224–247) to clear/deactivate laser first.

**Modified — shell/toolbar + bridge relay:**
- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml` — `ShellButton`
  `shellRunToolbarLaserButton` near the Script button (~lines 192–199); checked look via
  `selectedStyle`; opens the popover.
- Popover idiom reused from `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeFloatingToolbar.qml`
  (`actionPopover` ~lines 897–1294); active styling from
  `…/surface_controls/GraphSurfaceButton.qml` (~lines 23–26, 54–63); theme via `themeBridgeRef.palette`.
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py` — `laser_active` (pyqtProperty + notify),
  and the `graphics_laser_*` getters (see settings); extend `_GraphCanvasStateSource` protocol
  (~lines 51–91); existing `graphics_preferences_changed` (~line 499) drives live updates.
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py` — `set_laser_active(bool)`,
  `set_laser_mode(str)` slots forwarding to the active canvas.

**Modified — persistent settings:**
- `ea_node_editor/settings.py` — `"laser"` block in `DEFAULT_GRAPHICS_SETTINGS` (~lines 218–270)
  + MIN/MAX + defaults (~lines 149–177) = the locked values. `min_px/core_w/red_w` are **floats**;
  `fade_ms/idle_ms/glow/dot_r` ints.
- `ea_node_editor/app_preferences.py` — `normalize_laser_settings()` (clamp each field) called from
  `normalize_graphics_settings()` (~line 335); add to `__all__`. Persists to `app_preferences.json`
  (`%APPDATA%/COREX_Node_Editor/`, `app_preferences_path()` settings.py:343) via
  `AppPreferencesStore.persist_document`/`load_document` (~lines 628–641).
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py` — "Laser Pointer (Advanced)" section in
  `_build_canvas_page` (mirror `_make_section_title` + `_make_section_card` ~lines 209–216 +
  `QFormLayout`); populate in `set_values()` (~line 890); emit in `values()` (~line 1021).
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py` — existing
  `set_graphics_settings` (~line 125) / `update_graphics_settings` (~line 140) suffice; propagation
  via `host.apply_graphics_preferences`.

**Reused (no new styling):** `GraphSurfaceButton.qml`, `ShellButton.qml`, theme palette, the
`Shape`/`ShapePath` idiom from `EdgeRetainedLayer.qml`, `MultiEffect` usage from
`GraphNodeChromeBackground.qml` / `GraphNodeHeaderLayer.qml`.

> Line numbers are approximate anchors captured during planning — verify on the current tree.

## Execution Tasks

### T01 — Persistent "laser" settings: schema, normalization, bridge properties
- `settings.py`: add MIN/MAX constants + `DEFAULT_LASER_*` defaults (the locked values) and a
  `"laser"` block in `DEFAULT_GRAPHICS_SETTINGS`. Honor float vs int per the table.
- `app_preferences.py`: `normalize_laser_settings()` (deep-copy defaults, clamp each field; float
  clamps for `min_px/core_w/red_w`); call from `normalize_graphics_settings()`; export in `__all__`.
- `graph_canvas_state_bridge.py`: extend `_GraphCanvasStateSource`; add
  `@pyqtProperty(notify=graphics_preferences_changed)` getters `graphics_laser_fade_ms`,
  `…idle_ms`, `…min_px`, `…core_w`, `…red_w`, `…glow`, `…dot_r` reading from the canvas source with
  the `DEFAULT_GRAPHICS_SETTINGS["laser"]` fallbacks.
- **Preconditions:** none. **Deliverables:** defaults present; clamp on load; persist↔reload
  round-trips; bridge exposes `graphics_laser_*`. No UI yet.

### T02 — Graphics Settings dialog group
- `graphics_settings_dialog.py`: add a **"Laser Pointer (Advanced)"** section/card with rows for the
  seven fields (spinboxes for ints; `QDoubleSpinBox` or 0.5-step slider for the floats). Bind in
  `set_values()` / `values()`. Mirror the existing shadow/canvas section pattern.
- **Preconditions:** T01. **Deliverables:** dialog shows/edits the seven values; OK persists; reopen
  shows persisted values.

### T03 — Overlay component + mount
- Create `GraphLaserPointerOverlay.qml` porting the prototype: viewport-space top-most `Item`;
  `strokes`/`accumulating`/`ctrlDown` state; `beginStroke/feed/finishStroke(ctrl)/onCtrlReleased/
  clear`; min-distance filter (`min_px`), `maxPoints` ring-trim, `maxStrokes` cap; **active vs
  pinned Shape split**; `CurveRenderer`; soft glow `MultiEffect`; dot (radial gradient). Whole-stroke
  fade = idle `Timer(idle_ms)` → `NumberAnimation(fade_ms)` → `clear`. Bind tuning to the bridge
  `graphics_laser_*` props.
- Mount in `GraphCanvasRootLayers.qml` (last child, z:1200) bound to `canvasItem.laserModeActive` /
  `laserMode`; add `pushLaser…` forwarder.
- **Preconditions:** T01. **Deliverables:** with laser state forced on and points pushed manually
  (test/probe), the dot + neon multi-stroke render and fade correctly; live-edits to settings change
  the look.

### T04 — Interaction state + canvas wrappers + cursor
- `GraphCanvasInteractionState.qml`: add laser state + `setLaserActive/Mode/toggleLaser`.
- `GraphCanvas.qml`: aliases + wrappers + `pushLaser…`; `onLaserModeActiveChanged` cursor wiring
  (dot→Blank, line→Cross, off→clear) + `forceActiveFocus()`.
- **Preconditions:** T03. **Deliverables:** toggling laser state activates/deactivates the overlay
  and swaps cursor; deactivate clears.

### T05 — Input capture + Keys (hold-draw, Ctrl-pin, Esc)
- `GraphCanvasInputLayers.qml`: add `graphCanvasLaserCaptureArea` (top-most, gated on laser-active &
  no open menus, `AllButtons`, `hoverEnabled`). `moveDot` always; left-press `beginStroke` capturing
  `Qt.ControlModifier`; drag `feed`; release `finishStroke(ctrl)`. Track Ctrl via key events +
  mouse `modifiers`; Ctrl-release → fade pinned. Extend `Keys.onEscapePressed` to clear laser first.
  Re-grab focus on press so Ctrl-release is caught.
- **Preconditions:** T04. **Deliverables:** hold-drag draws and dissolves on release; Ctrl-drag pins
  multiple discontinuous lines; Ctrl-release dissolves all; Esc clears; no marquee/selection/node/
  edge/pan side effects while active.

### T06 — Toolbar button + Dot/Line popover + bridge relay
- `ShellRunToolbar.qml`: `shellRunToolbarLaserButton` opening the popover (Dot/Line toggles, selected
  highlighted). Selecting a mode → `set_laser_mode(...)` + `set_laser_active(true)`.
- `graph_canvas_command_bridge.py` / `graph_canvas_state_bridge.py`: `set_laser_active`/
  `set_laser_mode` slots + `laser_active` property; button `selectedStyle: …laser_active`.
- **Preconditions:** T04. **Deliverables:** button toggles tool; popover switches mode; checked-state
  reflects active.

### T07 — Tests, audit allowlist, polish
- Headless tests (offscreen) per the patterns in `tests/graph_surface/` +
  `tests/graph_surface_pointer_regression.py` (see Verification).
- If `graph_surface_pointer_audit` rejects the new `MouseArea`, allowlist
  `graphCanvasLaserCaptureArea`.
- Update agent maps if routing/ownership changed (per `AGENTS.md`): the graph-canvas subsystem map
  and relevant feature routes (input layers, floating toolbar/checked states, graphics settings).
- **Preconditions:** T01–T06. **Deliverables:** `pytest -n auto` green; manual checklist passes.

## Verification

**Automated (run with `pytest -n auto`; QML probes `QT_QPA_PLATFORM=offscreen`):**
- Settings round-trip (Python): defaults present; out-of-range clamped by `normalize_laser_settings`
  (incl. float fields); persist→reload identical; dialog `values()`↔`set_values()`.
- Bridge: `graphics_laser_*` return persisted values and re-notify on `graphics_preferences_changed`;
  `laser_active` reflects `set_laser_active`.
- Overlay state (QML probe): `setLaserActive/Mode` flip aliases; `feed` beyond `maxPoints`
  ring-trims; fade `NumberAnimation.duration == fade_ms`, idle `Timer.interval == idle_ms`;
  release → opacity→0 → `strokes` cleared.
- Ctrl-pin (QML probe): Ctrl held + two drags ⇒ `strokes.length == 2`, opacity stays 1; Ctrl release
  ⇒ fade starts; `Esc` ⇒ immediate clear.
- Input gating: synthesized press while laser-active ⇒ no marquee/selection (capture swallowed it).
- Toolbar/checked-state: clicking the laser button toggles the popover; Dot/Line click sets
  `laserMode`; `selectedStyle` tracks `laser_active`.
- Suite: `pytest -n auto` before finish.

**Manual smoke (run the app — prototype is the look/feel reference):**
1. Click Laser → popover; pick **Line** → crosshair cursor; hold-drag a curvy scribble — smooth,
   snappy, stays lit while held; release → ~110 ms hold then ~760 ms uniform dissolve.
2. **Ctrl**-hold, draw 3 separate strokes — all stay; release Ctrl → all dissolve together; redraw,
   then **Esc** → instant clear.
3. Pick **Dot** → only a glowing dot follows the cursor; OS cursor hidden; no trail.
4. Open Graphics Settings → "Laser Pointer (Advanced)"; change `red_w`/`glow`/`fade_ms`; reopen the
   tool — new values apply live; relaunch app — values persisted.
5. While laser active, click/drag does **not** select/move nodes or rubber-band; exit (Esc/tool
   switch) restores normal canvas input.
6. Zoom in/out — the dot and stroke widths stay constant (viewport space).

## Non-goals

- No persistence of the trail itself (ephemeral; no undo/redo; not in `.cxproj` documents).
- No multi-user/collaboration broadcast (local editor).
- No exposure of the four behavior toggles or coordinate space as user settings (locked).
- No color picker for the laser (fixed red) in this iteration — could be a later setting.
- No scene-pinned trail mode in this iteration (viewport space only).
- Dot mode has no trail and ignores Ctrl-pin.

## Risks and mitigations

- **Pinned-stroke rebuild cost.** Re-tessellating all pinned strokes every `feed` is wasteful →
  active/pinned Shape split (T03); cap `maxStrokes` ≈ 60 and `maxPoints` ≈ 400/stroke.
- **Ctrl-release / focus ownership.** Modifier-key *release* needs key focus on the input layer →
  re-grab focus on press and also track Ctrl via mouse `modifiers`; verify Ctrl-release fires after
  touching other widgets.
- **`graph_surface_pointer_audit` rejects the new MouseArea** → allowlist
  `graphCanvasLaserCaptureArea` (T07).
- **Pan/zoom mid-stroke (viewport space):** points are screen px; acceptable given sub-second life.
  Scene-pinned alt: store scene coords, scene-space wrapper using `viewBridge.zoom_value` + the
  translate formula in `GraphSelectionEnvelopeOverlay.qml` (lines 41–50), widths ÷ zoom (dot lags on
  pan) — not the chosen default.
- **Wheel-zoom / pan while active:** capture swallows mouse buttons (pan suppressed — exit to pan);
  wheel-zoom can remain if not consumed. Confirm desired during implementation.
- **Modal/popup opens while active:** keep drawing on top (z:1200) but disable capture via the
  `enabled:` guard so the modal stays interactive.
- **HiDPI:** keep all tuning values in logical px (the prototype's units).
- **Float settings:** `min_px/core_w/red_w` must round-trip as floats through normalization, the
  dialog widgets, and the bridge — don't coerce to int.

## Open questions (non-blocking; defaults chosen)

- Ctrl-release semantics — **chosen: dissolve all pinned lines** on Ctrl release. (Alt:
  keep-until-Esc.)
- Whether `CurveRenderer` / soft glow should become user toggles if low-end GPUs struggle — for now
  locked on, relying on the canvas perf-mode auto-degrade.

## Exact fresh-thread prompt (for the implementation session)

> Implement the laser pointer tool per `PLANS_TO_IMPLEMENT/in_progress/laser_pointer_tool.md`. The
> behavioral source of truth is the prototype `mockups/laser_pointer_notetaking_prototype.py` — reproduce its
> `strokes`/`accumulating`/`ctrlDown` state, `beginStroke/feed/finishStroke/onCtrlReleased/clear`
> logic, `PathMultiline` rendering, and whole-stroke fade-on-release exactly. Work task-by-task
> (T01→T07); run `pytest -n auto` and `QT_QPA_PLATFORM=offscreen` QML probes; start at
> `docs/agent_maps/INDEX.md` and update the affected maps. Do not make the trail persistent (it is
> ephemeral); only the seven numeric tuning values are persistent graphics settings. Verify the
> approximate line anchors against the current tree before editing.
