# Shared Graph Typography Token + Graphics Settings Control

## Summary
Add a single persisted graph-label base font-size setting and route all standard graph chrome text through a shared typography source instead of hardcoded QML sizes.

The new setting will live at `graphics.typography.graph_label_pixel_size`, default to `10`, and be exposed in Graphics Settings under the **Theme** page as a **Typography** control. Passive-node custom style overrides will remain authoritative where they already apply today.

## Key Changes
- Extend app preferences and defaults with:
  - `graphics.typography.graph_label_pixel_size: int`
  - Normalize/clamp it in `normalize_graphics_settings()` with an `8..18` range.
- Thread the new value through the existing shell/QML preference pipeline:
  - `ShellWorkspaceUiState`
  - workspace presenter apply/snapshot logic
  - `ShellWindow` Qt properties/state helpers
  - `GraphCanvasStateBridge`
  - `GraphCanvasRootBindings.qml` as a canvas-level `graphLabelPixelSize` binding
- Introduce a real shared graph typography source for QML, not scattered literals:
  - Centralize derived sizes/weights for graph chrome roles from one base value.
  - Preserve current visual hierarchy by deriving role sizes from the base token instead of making every text item identical.
  - Recommended derived roles:
    - standard node title: base `+2`
    - port labels: base
    - elapsed footer: base
    - inline property labels: base
    - badge text (`HALTED`, `OPEN`, inline status chips): `max(9, base-1)`
    - flow edge label text: base `+1`
    - flow edge pill text: base `+2`
    - exec arrow port label: base `+8`
- Refactor the current hardcoded graph chrome font usages to consume that shared source:
  - `GraphNodeHeaderLayer.qml`
  - `GraphNodePortsLayer.qml`
  - `GraphInlinePropertiesLayer.qml`
  - `GraphNodeHost.qml`
  - `EdgeFlowLabelLayer.qml`
- Keep passive style behavior intact:
  - `visual_style.font_size` / `font_weight` still control passive titles/body text where they already do.
  - The new global token applies to standard graph chrome on both active and passive nodes unless a passive-specific font path already exists.
- Add a new **Typography** card on the Graphics Settings **Theme** page:
  - One integer control for graph label size.
  - Use a `QSpinBox` with `8..18`.
  - Wire it into `set_values()` / `values()` roundtrips.

## Public Interfaces
- App-preferences schema addition:
  - `graphics.typography.graph_label_pixel_size`
- New Qt/QML bridge property:
  - `graphics_graph_label_pixel_size` on the Python-side graphics state bridge/source
  - `graphLabelPixelSize` on the QML canvas bindings/root side

## Test Plan
- Update dialog tests to verify:
  - default value is present
  - control roundtrips through `GraphicsSettingsDialog.values()`
  - invalid/missing persisted values normalize back to default
- Update preferences tests to verify:
  - persistence/load of the new `graphics.typography` block
  - host application receives the normalized size
- Extend bridge/QML preference regression coverage to verify:
  - the new property reaches QML
  - node title, port labels, elapsed footer, inline labels, and flow-edge labels respond to the shared size token
- Add a passive-style regression asserting:
  - passive `font_size` / `font_weight` overrides still win for passive text paths that already use them

## Assumptions
- The setting is size-only; no font-family picker.
- The control belongs in Graphics Settings > Theme > Typography.
- Passive-node custom font overrides are preserved, not replaced by the global setting.
- Existing relative text hierarchy should be preserved via derived tokens from one base size, not flattened to one literal size everywhere.
