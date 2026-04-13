# Path-Based Title Icons for Non-Passive Nodes

## Summary

Add title-leading icons for all non-passive nodes (`active` and `compile_only`) when their node spec references a supported image path. This applies to built-in and custom/plugin nodes, uses local `.svg`, `.png`, `.jpg`, or `.jpeg` files only, and keeps the current behavior of showing no icon when no usable path is defined.

The icon contract will be path-only for this feature:
- Built-ins use repo-managed asset paths.
- Custom/plugin nodes use absolute paths or plugin-root-relative paths.
- Old symbolic icon names are not rendered in the node header.
- Icons render before the node title, preserve aspect ratio, and use their authored colors.

## Implementation Changes

### 1. Node-spec contract and path resolution

- Keep `NodeTypeSpec.icon: str` as the authoring field, but treat it as an image-path reference for node-header icons.
- Support only local `.svg`, `.png`, `.jpg`, and `.jpeg` paths, case-insensitive.
- Add one central resolver on the Python side that converts `spec.icon` into a QML-safe local source URL string:
  - Absolute paths are used as-is if they exist and have a supported suffix.
  - Relative paths for custom/plugin nodes resolve from the plugin root.
  - Relative paths for built-in nodes resolve from a dedicated repo asset root for node title icons.
  - Missing file, unsupported suffix, unreadable file, or empty string resolves to `""`.
- Do not attempt to interpret symbolic names like `play_arrow` or `database` in the node header.
- Built-in migration rule: convert current non-passive built-in node specs that should show icons to repo-managed image paths; if a built-in node is left without a real path, it remains iconless.

### 2. Live graph payload and header rendering

- Extend the live graph node payload with a resolved snake_case field: `icon_source`.
- Populate `icon_source` only for eligible nodes:
  - `runtime_behavior` is `active` or `compile_only`
  - the resolved path is non-empty
- Leave passive nodes unchanged even if they carry an `icon` string.
- Update the graph header/title layer so the ordinary title row renders a generic `Image` before `titleText` using `nodeData.icon_source`.
- Size the icon from one effective pixel-size value, render with `PreserveAspectFit`, and keep layout stable:
  - title elision still works
  - centered titles remain centered with icon reserve width accounted for
  - icon visibility follows title visibility
- Keep the existing collapsed comment-backdrop icon path unchanged.
- Do not add node-library or inspector rendering changes in this pass.

### 3. Graphics Settings and effective sizing

- Add a new graphics typography preference: `graph_node_icon_pixel_size_override`.
- Type: nullable integer.
- Effective icon size rule:
  - if override is set, use it
  - if override is null, use the current `graph_label_pixel_size`
- Clamp the override using the same min/max range as `graph_label_pixel_size`.
- Thread this value through the existing graphics settings pipeline:
  - default settings
  - preference normalization/clamping
  - graphics settings dialog round-trip
  - canvas/QML bridge
  - shared graph typography consumer
- Graphics Settings UI:
  - add a checkbox or equivalent toggle for “custom node icon size”
  - when off, the icon auto-matches title size
  - when on, a spinbox sets the explicit pixel size

### 4. Built-in asset organization

- Add a dedicated repo asset folder for node title icons, SVG preferred.
- Name built-in asset files predictably from their migrated node icon meaning so built-in specs can reference stable relative paths.
- Prefer SVG assets for built-ins; allow PNG/JPG/JPEG only when SVG is not available.
- Render all path-based icons without theme tinting.

## Test Plan

- Resolution tests:
  - absolute SVG path resolves
  - plugin-root-relative PNG/JPG/JPEG path resolves
  - missing path resolves to empty source
  - unsupported suffix resolves to empty source
- Eligibility tests:
  - `active` node with valid path gets `icon_source`
  - `compile_only` node with valid path gets `icon_source`
  - `passive` node does not get a rendered title icon
- Settings tests:
  - default/null override follows `graph_label_pixel_size`
  - explicit override persists and clamps correctly
  - dialog values round-trip through preferences and canvas bridge
- UI/visual checks:
  - icon appears before the title on expanded non-passive nodes
  - icon remains correctly aligned when titles are centered or elided
  - missing/unreadable path shows no icon and does not break layout
  - collapsed comment-backdrop icon behavior is unchanged
  - SVG, PNG, and JPEG examples all render at the configured size

## Assumptions and Defaults

- “Non-passive” means `runtime_behavior != "passive"`, so this includes `compile_only`.
- Header-icon support is local-file-only; no remote URLs, data URIs, or symbolic icon-name rendering.
- Missing or invalid icon paths fail silently to “no icon”.
- Custom/plugin relative paths resolve from the plugin root.
- Built-in nodes are migrated to path-based assets where paths are defined; nodes without a real path continue to show no icon, matching today’s behavior.
