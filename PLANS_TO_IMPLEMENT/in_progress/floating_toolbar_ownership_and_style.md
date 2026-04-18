# Floating Toolbar — Ownership Caret + Selectable Button Styles

> Visual reference: [`node_overlay_button_style_variants.html`](../../node_overlay_button_style_variants.html)
> Follow-up to: [`floating_node_toolbar.md`](./floating_node_toolbar.md)
>
> **Selected ownership cue:** Cue **A — Pointer beak (caret)**
> **Selected default style:** Variant **2 — Icon-only compact pill**
> **User-selectable styles (Graphics settings):** Variants **2**, **4 (Segmented bar)**, **6 (Minimal ghost row)**

## Context

The floating toolbar shipped in commit `277f864` (`GraphNodeFloatingToolbar.qml`) uses the Variant 1 rounded-rect chrome with per-button accent borders. Two gaps remain from the `node_overlay_button_style_variants.html` review:

1. **Ownership is ambiguous on dense graphs.** When the toolbar floats in the gap between two nodes it isn't obvious which node it acts on — rename/delete can fire on the wrong target. The HTML captures this in the *Before/After* demo.
2. **One-size chrome doesn't fit every graph.** Data-heavy graphs benefit from the compact pill (Variant 2); orderly lists read better as a segmented bar (Variant 4); dense graphs with lots of overlays want the minimal ghost row (Variant 6).

Outcome: the toolbar always shows a small **caret pointing at the owner node** (Cue A), and users can switch chrome style from Graphics settings between three curated options, with **Variant 2 (icon-only compact pill)** as the default.

## Design

### 1. Ownership caret (always-on, Cue A)

A 9×9 square rotated 45° rendered as a Rectangle inside `GraphNodeFloatingToolbar.qml`. It sits on the toolbar's **bottom** edge when the toolbar is above the owner (default) and on the **top** edge when the toolbar is flipped below (mirrors HTML lines 234-248). The beak inherits the active chrome's `color` and `border.color` so it works for all three chrome styles.

Horizontal center tracks `nodeLocalRect.x + nodeLocalRect.width / 2 - toolbar.x` so it points at the owner's center even when the toolbar shifts horizontally near the viewport edge (`toolbar_positioning.js` already clamps x — the beak just reads the resulting delta).

### 2. Three selectable chrome styles

Drive chrome appearance from a new string property `root.style` on `GraphNodeFloatingToolbar.qml` with three branches. The `GraphSurfaceButton` API already has enough knobs (`iconOnly`, `baseFillColor`, `baseBorderColor`, `chromeRadius`, `contentHorizontalPadding`, `contentVerticalPadding`) — **no changes to `GraphSurfaceButton.qml` are required**. All styles show icons only (no text labels); tooltips already carry the labels.

| Style id | HTML variant | Chrome | Button |
|---|---|---|---|
| `compact_pill` *(default)* | V2, lines 540-568 | `radius: 999`, `rgba(22,26,36,0.96)` bg, `rgba(255,255,255,0.06)` border, `shadow-md` | 28×28, `radius: 999`, transparent base, hover `rgba(77,168,218,0.18)` |
| `segmented_bar` | V4, lines 599-629 | `radius: 7`, `#1a1f2a` bg, `#2b3142` border, `overflow: hidden` | `radius: 0`, 1px right divider (`#242a38`), destructive gets left divider |
| `minimal_ghost` | V6, lines 660-692 | No chrome (`transparent`, `border: none`) | 26×26, `radius: 5`, transparent base, 1px vertical separator before destructive button |

Per the HTML `.cue-a` recipe, the caret uses the chrome's `color` and accent border when a chrome exists. For `minimal_ghost` (no chrome) the caret inherits `root.accentColor` at 0.55 alpha so ownership is still legible on the bare button row.

### 3. Setting plumbing (follows the `graphics_performance_mode` pattern exactly)

New enum `FLOATING_TOOLBAR_STYLE_CHOICES = (("compact_pill", "Compact pill"), ("segmented_bar", "Segmented bar"), ("minimal_ghost", "Minimal ghost"))`. Default = `"compact_pill"`. Stored under `graphics.canvas.floating_toolbar_style` (same section as the other overlay toggles — `show_grid`, `show_minimap`, `show_port_labels`).

The value rides the existing rails end-to-end:

```
settings.DEFAULT_GRAPHICS_SETTINGS["canvas"]["floating_toolbar_style"]
  → app_preferences.normalize_graphics_settings (new normalize_floating_toolbar_style)
  → ShellWorkspaceUiState.floating_toolbar_style (state.py)
  → ShellWorkspacePresenter.graphics_floating_toolbar_style (workspace_presenter.py)
  → GraphCanvasPresenter.graphics_floating_toolbar_style + set_… (graph_canvas_presenter.py)
  → ShellWindow.graphics_floating_toolbar_style pyqtProperty (window.py / window_state_helpers.py)
  → window_state.run_and_style_state.set_graphics_floating_toolbar_style
  → GraphCanvasStateBridge.graphics_floating_toolbar_style pyqtProperty
  → GraphNodeFloatingToolbar.qml reads the bridge and switches chrome
```

### 4. Graphics Settings dialog UI

On the Canvas page under a new "Floating toolbar" sub-section (beneath the existing "Overlay" card), render a `QComboBox` labelled "Floating toolbar style" with the three choices. Keep it a combo (not radio cards like performance mode) — this is a visual preference, not a mode with trade-off copy. One-line helper label: *"Chrome style for the hover toolbar above nodes."*

## Critical Files

**Modified — Python settings / plumbing:**
- `ea_node_editor/settings.py` — add `FLOATING_TOOLBAR_STYLE_CHOICES`, `DEFAULT_FLOATING_TOOLBAR_STYLE`, and `floating_toolbar_style` to `DEFAULT_GRAPHICS_SETTINGS["canvas"]` (lines 126-138).
- `ea_node_editor/app_preferences.py` — add `normalize_floating_toolbar_style`; call it inside `normalize_graphics_settings` alongside `normalize_grid_overlay_style` (around line 166); export from `__all__` (line 518).
- `ea_node_editor/ui/shell/presenters/state.py` — add `floating_toolbar_style: str` to `ShellWorkspaceUiState` (line 25) and populate it in `build_default_shell_workspace_ui_state` (line 44), alongside `grid_style`.
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py` — expose `graphics_floating_toolbar_style` getter (around line 62).
- `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py` — expose getter + `set_graphics_floating_toolbar_style` (mirror lines 46 / 99).
- `ea_node_editor/ui/shell/presenters/contracts.py` — add `set_graphics_floating_toolbar_style` to the protocol (line 55 neighborhood).
- `ea_node_editor/ui/shell/window.py` — add pyqtProperty `graphics_floating_toolbar_style` (mirror line 271).
- `ea_node_editor/ui/shell/window_state_helpers.py` — add `_qt_graphics_floating_toolbar_style` (mirror line 81).
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py` — add `set_graphics_floating_toolbar_style` setter (mirror line 83).

**Modified — QML bridges:**
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py` — add `graphics_floating_toolbar_style` pyqtProperty (mirror `graphics_performance_mode` at line 280).
- `ea_node_editor/ui_qml/graph_canvas_bridge.py` — re-export property (mirror `graphics_show_tooltips` at line 161).

**Modified — Settings dialog:**
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py` — add "Floating toolbar" section to `_build_canvas_page` (line 177); add `self.floating_toolbar_style_combo` (mirror `grid_style_combo` at line 193); wire into `set_values` (line 621) and `values` (line 686).

**Modified — QML toolbar:**
- `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeFloatingToolbar.qml` — read style from bridge (new readonly `style`), conditionally style `chromeContainer` (lines 172-190), feed per-style props into the `GraphSurfaceButton` Repeater (lines 200-222), add the caret Rectangle with flip-aware anchoring.

**Reused (no changes):**
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceButton.qml` — existing `iconOnly`, `chromeRadius`, `baseFillColor`, `baseBorderColor`, `hoverFillColor` props cover all three variants.
- `ea_node_editor/ui_qml/components/graph/overlay/toolbar_positioning.js` — caret reads `root.flipped` which this file already sets.

**New / extended tests:**
- `tests/test_app_preferences.py` — add a case for `normalize_floating_toolbar_style` (valid → passes; unknown → default).
- `tests/test_graphics_settings_preferences.py` — extend the roundtrip test to carry `floating_toolbar_style` end-to-end through `ShellWorkspaceUiState` and `GraphCanvasStateBridge`.
- `tests/test_graphics_settings_dialog.py` — assert the combo is present and `set_values` / `values` round-trip the three ids.

## Execution Tasks

**S01 — Settings scaffolding.** Add choices, default, `normalize_floating_toolbar_style`, roundtrip tests. No UI yet. Deliverable: `pytest -n auto tests/test_app_preferences.py tests/test_graphics_settings_preferences.py` green with new cases.

**S02 — Presenter + bridge plumbing.** Wire the field through `ShellWorkspaceUiState`, presenters, `ShellWindow` pyqtProperty, `GraphCanvasStateBridge`. No QML read yet. Deliverable: bridge exposes `graphics_floating_toolbar_style` reflecting preferences.

**S03 — Graphics settings dialog control.** Add the Canvas-page combo, round-trip tests. Deliverable: user can pick a style; value persists to `app_preferences.json`.

**S04 — Toolbar caret (Cue A).** Add the beak Rectangle to `GraphNodeFloatingToolbar.qml`, flipping with `root.flipped`. No style switching yet. Deliverable: current Variant-1 chrome with a caret pointing at the owner.

**S05 — Compact pill (default) + style branching.** Replace the current chrome recipe with the three-branch logic driven by `root.style`. Make `compact_pill` the resolved default when the bridge reports no value. Deliverable: all three styles render correctly in a running shell; switching in Graphics settings applies live.

**S06 — Cleanup + regression pass.** Delete the old Variant-1 hard-coded styling, run full graph-surface test suite, manual smoke in the shell across pan/zoom/flip/drag.

## Verification

1. `pytest -n auto tests/test_app_preferences.py tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py tests/test_floating_toolbar_positioning.py` — all green.
2. `pytest -n auto tests/graph_surface` — no regressions in toolbar-adjacent suites.
3. Launch the shell, hover a node → caret points at the correct node; drag the node → caret tracks the owner's center even when the toolbar clamps horizontally near the viewport edge.
4. Scroll a node near the viewport top so the toolbar flips below → caret flips to the top edge and still points at the owner.
5. Open **Graphics Settings → Canvas → Floating toolbar**; cycle through the three styles. Each applies without restart; buttons remain clickable; tooltips still show.
6. Quit and relaunch → selection persists (written in `%APPDATA%/COREX_Node_Editor/app_preferences.json` under `graphics.canvas.floating_toolbar_style`).

## Out of Scope

- Cue B (owner accent echo), Cue C (overlap anchor), Cue D (width-match flush), Cue E (dim neighbors) — deliberately left out; only Cue A was selected.
- Variants 1, 3, 5, 7 — not offered in the picker.
- Adding per-theme toolbar palettes; the bridge already carries `nodeThemeColor` and all three chrome recipes use it for accent/hover.
