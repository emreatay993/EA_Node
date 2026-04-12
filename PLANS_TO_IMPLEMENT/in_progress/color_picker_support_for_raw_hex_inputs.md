# Add Color Picker Support to Remaining Raw Hex Inputs

## Summary
- Keep the existing color UX as the standard: manual hex entry plus a clickable swatch that opens the native Qt color dialog with alpha.
- Treat the remaining gap as a QML editor-pipeline issue, not a style-dialog rewrite: the existing passive node, flow edge, and graph theme dialogs already use the shared picker widget.
- Upgrade all remaining raw hex entry points by adding first-class `color` editor modes to the node inspector and inline property editors, and audit for any missed QWidget raw hex fields.

## Key Changes
- Schema and metadata:
  - Extend node editor metadata to support `color` in both inline and inspector editor modes.
  - Keep color support explicit: only properties marked with `inline_editor="color"` or `inspector_editor="color"` get the picker.
  - Do not add key-name heuristics; untagged string properties remain plain `text`.
- Inspector path:
  - Add a reusable QML inspector color field that shows a swatch/button plus the hex text value.
  - Add an inspector bridge method that opens the native `QColorDialog`, preloads the current value when valid, enables alpha, and returns the chosen value serialized in the same format as the existing widget control.
  - Commit the chosen value through the normal `set_selected_node_property` flow.
- Inline property path:
  - Add a reusable graph-surface color field for `inline_editor === "color"`.
  - Mirror the existing path-browse bridge pattern with a node-surface color-pick method that opens the same native dialog and commits through the normal inline property update flow.
  - Keep manual text edits valid for `#RRGGBB` and `#AARRGGBB`, matching current validation and serialization behavior.
- Audit and adoption:
  - Search current built-in node specs for real color properties and tag them explicitly where they exist.
  - If any remaining QWidget dialogs still use raw hex `QLineEdit`s, replace those fields with the existing shared color widget; otherwise leave current style/theme dialogs unchanged.
  - Add at least one test fixture property marked as `color` so the new pipeline is covered even if built-in nodes currently do not expose a color property.

## Public Interface Changes
- Add `color` to the supported inline editor mode set.
- Add `color` to the supported inspector editor mode set.
- Add bridge APIs for picking a color from QML in both inspector and inline-editor contexts, returning a normalized hex string or an empty string when cancelled.

## Execution Tasks

### T01 Metadata and editor-mode contract
- Goal: extend the editor metadata contract so `inline_editor="color"` and `inspector_editor="color"` resolve as first-class color editors without changing the behavior of untagged string properties.
- Preconditions: none.
- Conservative write scope: property/editor metadata normalization, editor-mode resolution helpers, and the narrow tests that prove explicit color opt-in versus default text handling.
- Deliverables: explicit `color` support in the metadata/resolver layer plus unit coverage for explicit `color` and untagged string cases.
- Verification: resolver/metadata tests covering explicit `color`, fallback `text`, and normalized `#RRGGBB` / `#AARRGGBB` handling under the supported editor modes.
- Non-goals: no QML control work and no QWidget dialog audit in this task.
- Packetization notes: clean `P01` boundary because both inspector and inline surfaces depend on this contract.

### T02 Inspector color control and bridge
- Goal: add a reusable inspector color field and native-dialog bridge path for properties marked with `inspector_editor="color"`.
- Preconditions: T01.
- Conservative write scope: inspector QML/editor components plus the selected-node property bridge and commit path used by inspector edits.
- Deliverables: inspector swatch/button UI, native `QColorDialog` integration with alpha, current-value preload when valid, and normalized commit/cancel handling.
- Verification: inspector rendering coverage plus a mocked picker-bridge test that asserts the chosen color commits through the existing selected-node property flow.
- Non-goals: no inline graph-surface controls in this task.
- Packetization notes: clean `P02` boundary and the preferred place to establish the shared dialog/serialization pattern that inline editing can mirror later.

### T03 Inline color control and bridge
- Goal: add the graph-surface color control for properties marked with `inline_editor="color"` and route it through the normal inline property update flow.
- Preconditions: T01 and the dialog/serialization conventions established in T02.
- Conservative write scope: graph-surface inline property QML/components plus the node-surface bridge and inline property mutation path.
- Deliverables: inline color control with manual hex entry, native dialog selection, and normalized commit behavior that matches the inspector path.
- Verification: inline-layer rendering coverage plus a mocked inline picker test that asserts the chosen color commits through the existing inline property update flow.
- Non-goals: no built-in node tagging audit and no QWidget leftover cleanup in this task.
- Packetization notes: clean `P03` boundary; if the scope stays small, this is the first candidate to merge with T02.

### T04 Audit, adoption, and regression closeout
- Goal: tag real color properties explicitly, replace any true leftover raw hex QWidget fields if they still exist, and close the regression/serialization coverage for the full color-editing path.
- Preconditions: T02 and T03.
- Conservative write scope: built-in node specs with real color properties, any remaining raw hex QWidget fields found by audit, and the regression/serialization tests needed to close the feature safely.
- Deliverables: explicit color annotations where needed, cleanup of true leftover raw hex entry points only, and regression coverage for passive style, flow edge style, graph theme, and serialized hex round-trips.
- Verification: existing passive style, flow edge style, and graph theme editor tests stay green, plus new round-trip checks for uppercase `#RRGGBB` and `#AARRGGBB` values.
- Non-goals: no custom preset palette UI and no rewrite of dialogs that already use the shared picker.
- Packetization notes: clean `P04` closeout boundary because it can absorb the final audit, adoption, and verification evidence without reopening the earlier contract tasks.

## Work Packet Conversion Map
1. `P00 Bootstrap`: create the packet-set manifest, status ledger, prompt files, and index registration if this plan is later packetized.
2. `P01 Metadata and editor-mode contract`: derived primarily from T01.
3. `P02 Inspector color path`: derived primarily from T02.
4. `P03 Inline color path`: derived primarily from T03.
5. `P04 Audit and verification closeout`: derived primarily from T04.

## Test Plan
- Unit tests:
  - Verify explicit `color` metadata resolves to `color`.
  - Verify untagged string properties still resolve to `text`.
- Inspector tests:
  - Add a fixture with `inspector_editor="color"`.
  - Verify the inspector renders the color control instead of the plain text field.
  - Mock the picker bridge and assert the selected color is committed to the node property.
- Inline editor tests:
  - Add a fixture with `inline_editor="color"`.
  - Verify the inline layer renders the new color control.
  - Mock the inline picker bridge and assert the chosen color is committed.
- Regression tests:
  - Keep current passive style, flow edge style, and graph theme editor tests green.
  - Add one round-trip/serialization check for uppercase `#RRGGBB` and `#AARRGGBB` values.

## Assumptions
- “Palette selection” means reusing the existing swatch + native color dialog behavior, not building a custom preset palette UI.
- Manual hex entry remains supported alongside the picker.
- Existing style/theme dialogs are already on the correct picker path and should only change if the audit finds a true leftover raw hex field.
