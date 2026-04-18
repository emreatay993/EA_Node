# Property Pane Variants — V12 / V15 / V16 from COREX design bundle

> **Design reference:** `property-pane-corex/project/Property Pane Variants v2.html` (fetched from
> `https://api.anthropic.com/v1/design/h/cC-W_RKQgfKtBVZnQ4ObEQ?open_file=Property+Pane+Variants+v2.html`).
> Bundle extracted to `C:\Users\emre_\AppData\Local\Temp\design_bundle\property-pane-corex\`.
>
> **Implemented variants** (selected from the V2 board):
> - `smart_groups` — **12 · Smart Groups (Modified / Driven pinned)** — `variants/variants-11-15.jsx` lines 131–220
> - `accordion_cards` — **15 · Accordion Cards + Search-in-Group** — `variants/variants-11-15.jsx` lines 392–482
> - `palette` — **16 · Palette Only (inline editors)** — `variants/variants-16-20.jsx` lines 45–142
>
> **Classic layout is retired** (per user). Default = `smart_groups`.
>
> Source design CSS: `styles/pane.css`, tokens already mirrored in `ea_node_editor/ui/theme/tokens.py`
> (app_bg, panel_bg, panel_alt_bg, toolbar_bg, input_bg, accent, muted_fg, inspector_card_bg,
> inspector_section_header_bg, inspector_selected_bg, etc.). Variants MUST read these via
> `root.themePalette.*` — no hardcoded colors.

## Summary

Three selectable Inspector / Property Pane layouts ship behind a new `graphics.shell.property_pane_variant`
preference. Users pick among **Smart Groups**, **Accordion Cards**, and **Palette** in Graphics Settings →
Theme. Every variant renders through `ShellInspectorBridge` and respects the active shell theme (Stitch Dark
/ Stitch Light) by consuming `root.themePalette` tokens exclusively.

Grouping data (Source / Selection / Post in the mocks) comes from a new optional `group: str = ""` field on
`PropertySpec`. Empty groups fall back to one synthetic `"Properties"` bucket so variants degrade gracefully
until individual node specs are annotated.

The plan mirrors the `floating_toolbar_style` plumbing pattern (see
[floating_toolbar_ownership_and_style.md](../../PycharmProjects/EA_Node_Editor/PLANS_TO_IMPLEMENT/in_progress/floating_toolbar_ownership_and_style.md))
end-to-end rather than inventing a new rail.

## Key Changes

- New `PROPERTY_PANE_VARIANT_CHOICES` / `DEFAULT_PROPERTY_PANE_VARIANT = "smart_groups"` in
  `ea_node_editor/settings.py`, stored under `graphics.shell.property_pane_variant`.
- Normalization + push through `ShellWorkspaceUiState` → `ShellHostPresenter` → `ShellWindow` →
  `ShellInspectorBridge` pyqtProperty → QML `inspectorBridgeRef.property_pane_variant`.
- Graphics Settings dialog gains a "Property pane" combo on the **Theme** page under a new "Inspector"
  section. Label + helper copy: *"Layout for the property / inspector pane."*
- `PropertySpec` gains an optional `group: str = ""` field; `build_selected_node_property_items` emits
  `"group"` in every property item payload (empty → `"Properties"`).
- New shared QML primitives in `ea_node_editor/ui_qml/components/shell/` used by every variant:
  `InspectorChevron.qml`, `InspectorFilterBar.qml`, `InspectorScopeToggle.qml`,
  `InspectorSmartGroupHeader.qml`, `InspectorOverrideBadge.qml`, and a small
  `InspectorFilter.js` helper (`makePropMatcher(query, scope)`, `groupPropertyItems(items)`).
- Three new variant body components render the property list:
  `InspectorSmartGroupsBody.qml`, `InspectorAccordionCardsBody.qml`, `InspectorPaletteBody.qml`.
  Each takes `pane`, `propertyItems` and emits no new bridge calls — they reuse the same
  `set_selected_node_property` / `browse_selected_node_property_path` slots by delegating to
  `InspectorPropertyEditor` (our existing editor atom).
- `InspectorPane.qml` replaces the property portion of `InspectorNodeDefinitionSection` with a `Loader`
  that picks one of the three variant bodies by `inspectorBridgeRef.property_pane_variant`. Node header
  (title / subtitle / metadata chips) + port management stay shared.

## Public Interface Changes

- `ea_node_editor.settings`:
  - new exports `PROPERTY_PANE_VARIANT_CHOICES`, `DEFAULT_PROPERTY_PANE_VARIANT`.
  - `DEFAULT_GRAPHICS_SETTINGS["shell"]["property_pane_variant"]`.
- `ea_node_editor.app_preferences`:
  - new exported `normalize_property_pane_variant` called inside `normalize_graphics_settings`.
- `ea_node_editor.nodes.node_specs.PropertySpec`:
  - new `group: str = ""` field (last non-defaulted positional; safe for all existing dataclass constructions
    which are all kwarg).
- `ShellInspectorBridge`:
  - new `property_pane_variant` `pyqtProperty(str, notify=inspector_state_changed)` reflecting the pref.
- `ShellInspectorPresenter`:
  - tracks `_property_pane_variant` and exposes `property_pane_variant` getter plus
    `set_property_pane_variant(value: str)` that emits `inspector_state_changed`.

## Execution Tasks

### T01 Settings Plumbing (variant preference end-to-end, no render change)

- Goal: push a validated `property_pane_variant` string from `app_preferences.json` all the way to
  `ShellInspectorBridge` as a pyqtProperty, without changing any rendered UI yet. Establishes the rail
  so later tasks only touch the QML seam.
- Preconditions: none.
- Conservative write scope:
  - `ea_node_editor/settings.py` — add choices constant + default + `DEFAULT_GRAPHICS_SETTINGS["shell"]
    ["property_pane_variant"]` (next to `tab_strip_density`).
  - `ea_node_editor/app_preferences.py` — add `normalize_property_pane_variant`; call inside
    `normalize_graphics_settings`; re-export via `__all__`.
  - `ea_node_editor/ui/shell/presenters/state.py` — add `property_pane_variant: str` to
    `ShellWorkspaceUiState`; populate in `build_default_shell_workspace_ui_state`.
  - `ea_node_editor/ui/shell/presenters/inspector_presenter.py` — add
    `_property_pane_variant` attribute, `property_pane_variant` getter,
    `set_property_pane_variant(variant)` that emits `inspector_state_changed` on change.
  - `ea_node_editor/ui/shell/presenters/host_presenter.py` — on `apply_graphics_preferences`, forward
    `graphics.shell.property_pane_variant` to the inspector presenter.
  - `ea_node_editor/ui_qml/shell_inspector_bridge.py` — add `property_pane_variant`
    `pyqtProperty(str, notify=inspector_state_changed)`.
- Deliverables: plumbing landing; smoke test in `tests/test_app_preferences.py` that asserts
  `normalize_graphics_settings` fills `shell.property_pane_variant` with the default when absent and
  rejects unknown values.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest -n auto tests/test_app_preferences.py -q`
  - `.\venv\Scripts\python.exe -m pytest -n auto tests/test_inspector_reflection.py tests/test_window_library_inspector.py -q`
  - App starts; no visible change.
- Non-goals: no QML changes, no dialog UI, no PropertySpec edits, no new variants.
- Packetization notes: → `P01`. Mirrors the first half of `floating_toolbar_style` (settings + presenter +
  bridge) but stops short of the QML read.

### T02 PropertySpec `group` field + payload emission

- Goal: let every property item the inspector sees carry a group label (default `""`) so variant bodies
  can cluster rows. Back-fill is optional per-node spec and out of scope here.
- Preconditions: T01 landed (not strictly required but avoids noisy merges).
- Conservative write scope:
  - `ea_node_editor/nodes/node_specs.py` — add `group: str = ""` to `PropertySpec`; update `to_payload` /
    `from_value` if they exist for PropertySpec; touch no concrete spec definitions yet.
  - `ea_node_editor/ui/shell/window_library_inspector.py:706 build_selected_node_property_items` — emit
    `"group": (prop.group or "Properties")` in each item dict.
  - `tests/test_window_library_inspector.py` — add assertion that the payload includes `"group"` with
    fallback `"Properties"` when unset.
- Deliverables: PropertySpec + payload carry group metadata; fallback guaranteed.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest -n auto tests/test_window_library_inspector.py tests/test_inspector_reflection.py -q`
- Non-goals: annotating actual node specs (separate follow-up); no UI changes.
- Packetization notes: → `P02`. Independent of T01; can land first or second with trivial merge.

### T03 Graphics Settings dialog — Property pane combo

- Goal: expose the variant picker in Graphics Settings → Theme so users can pick a layout.
- Preconditions: T01 landed (needs the choices constant).
- Conservative write scope:
  - `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`:
    - extend imports: `PROPERTY_PANE_VARIANT_CHOICES`.
    - inside `_build_theme_page` (line 531), **after** the Typography card, add a new "Inspector"
      section title + card with `QFormLayout`; a `QComboBox` populated from
      `PROPERTY_PANE_VARIANT_CHOICES`; object name `graphicsSettingsPropertyPaneVariantCombo`; helper
      label reading *"Layout for the property / inspector pane."*.
    - `set_values`: read from `settings["shell"]["property_pane_variant"]`, `findData`, set current.
    - `values`: write back `shell.property_pane_variant`.
  - `tests/ui/dialogs/test_graphics_settings_dialog.py` (or the existing equivalent; reuse qtbot fixture
    in `conftest.py`) — test round-trip (default loads; user selects; values returns the new id).
- Deliverables: the combo renders in the dialog, persists through `app_preferences_controller`.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest -n auto tests/ui/dialogs/test_graphics_settings_dialog.py -q`
  - Manual: open Graphics Settings → Theme; change combo; click OK; reopen dialog; selection persists.
- Non-goals: QML wiring (still no visible change in the pane).
- Packetization notes: → `P03`. Forward-only dependency on T01.

### T04 Shared QML primitives + filter helper

- Goal: port the reusable atoms from `variants/shared.jsx` and `styles/pane.css` into QML primitives that
  every variant body can consume. No business logic yet.
- Preconditions: none (pure additions).
- Conservative write scope — all new files under `ea_node_editor/ui_qml/components/shell/`:
  - `InspectorChevron.qml` — 10×10 chevron with `open` bool, 100 ms rotation; mirrors
    `variants/shared.jsx:9-17`.
  - `InspectorOverrideBadge.qml` — pill badge showing "Driven", accent-tinted; mirrors
    `shared.jsx:70-72` + pane.css `.override-badge`.
  - `InspectorScopeToggle.qml` — Name / Value segmented toggle, active button tinted via
    `inspector_selected_bg`; mirrors `shared.jsx:246-287`.
  - `InspectorFilterBar.qml` — search icon + text input + optional clear ✕ + embedded
    `InspectorScopeToggle`. Emits `queryChanged(string)` / `scopeChanged(string)`; mirrors
    `shared.jsx:289-329`.
  - `InspectorSmartGroupHeader.qml` — 7-px tall collapsible row with chevron, accent left border,
    label + count; mirrors `variants-11-15.jsx:143-159`.
  - `InspectorFilter.js` — pure JS helpers:
    - `makePropMatcher(query, scope)` (see `shared.jsx:231-244`),
    - `groupPropertyItems(items)` (returns `[{ name, items }]` preserving order of first-seen group),
    - `smartGroups(items)` → `[{ kind, label, accent, items }]` for Modified / Driven / Required.
  - Extend `MainShellUtils.js` only if import resolution requires it (prefer the new file).
- Deliverables: compilable QML primitives; colors read from `pane.themePalette.*` exclusively; no hard
  hex values outside SVG glyph data-uris (chevron stroke reads `currentColor`).
- Verification:
  - `.\venv\Scripts\python.exe -m pytest -n auto tests/main_window_shell/ -q -k "shell or theme"`
    (smoke — no new tests yet, just ensure QML compiles at startup).
  - Manual: launch the app; no visible change (new primitives not consumed yet); no QML warnings in console.
- Non-goals: variant bodies, wiring, dialog changes.
- Packetization notes: → `P04`. Independent of T01–T03; forward-only.

### T05 V12 Smart Groups body (`smart_groups`)

- Goal: build `InspectorSmartGroupsBody.qml` as the default rendering target. Shows pinned smart groups
  (Modified / Driven / Required — only when non-empty) followed by static category groups.
- Preconditions: T02 (items have `group`), T04 (primitives).
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/shell/InspectorSmartGroupsBody.qml` — new component.
  - Properties: `pane`, `propertyItems` (model = the bridge's `selected_node_property_items`).
  - Renders:
    - `InspectorFilterBar` at top (binds a local `filterQuery` / `filterScope`).
    - Smart groups: three conditional `InspectorSmartGroupHeader` + body Columns; accent per kind
      (`edge_warning` for Modified, `accent` for Driven, `run_failed` for Required). Populated via
      `InspectorFilter.js:smartGroups`.
    - Static groups: iterate `InspectorFilter.js:groupPropertyItems(filteredItems)`; each group gets a
      header + Column of existing `InspectorPropertyEditor` instances.
  - Local state: `expandedMap` keyed by group label; default all expanded.
  - `tests/test_inspector_smart_groups_variant.py` (new) — instantiate the QML component with a stubbed
    `ShellInspectorBridge` via `qtbot`; assert smart groups show when `overridden_by_input` / `dirty` /
    `required` items are present.
- Deliverables: the component compiles and renders a reference node; pixel-parity with
  `variants-11-15.jsx:131-220` for header / section-header chrome (verified visually against the HTML
  cold, not via screenshot).
- Verification:
  - `.\venv\Scripts\python.exe -m pytest -n auto tests/test_inspector_smart_groups_variant.py tests/test_inspector_reflection.py -q`
  - Manual: set `property_pane_variant = "smart_groups"` and confirm real node properties render with
    the group label from T02.
- Non-goals: hook into `InspectorPane.qml` (reserved for T08); other variants.
- Packetization notes: → `P05`. Depends on T02 + T04.

### T06 V15 Accordion Cards + Search-in-Group body (`accordion_cards`)

- Goal: build `InspectorAccordionCardsBody.qml`: one collapsible card per group; per-group inline filter
  appears when the global filter is empty and the group has > 3 properties.
- Preconditions: T02, T04.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/shell/InspectorAccordionCardsBody.qml` — new component; reuses
    `InspectorFilterBar`, `InspectorSmartGroupHeader` (we render the group name inside a card chrome;
    see `variants-11-15.jsx:431-480`). Card outer: radius 8, `panel_bg`, `border` token.
  - Tracks per-group open state + per-group query map.
  - `tests/test_inspector_accordion_cards_variant.py` (new) — qtbot test that toggling a header flips
    the Column visibility; per-group filter shows only when relevant.
- Deliverables: compilable variant, visible parity with `variants-11-15.jsx:392-482`.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest -n auto tests/test_inspector_accordion_cards_variant.py tests/test_inspector_reflection.py -q`
- Non-goals: touching `InspectorPane.qml` (T08), Smart Groups.
- Packetization notes: → `P06`. Depends on T02 + T04. Independent of T05.

### T07 V16 Palette-only body (`palette`)

- Goal: build `InspectorPaletteBody.qml`: top-level search input with scope toggle, streams flat filtered
  property rows beneath the query with inline editors, one active/highlighted row with accent border,
  keyboard Up / Down / Enter support; footer hints strip.
- Preconditions: T02, T04.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/shell/InspectorPaletteBody.qml` — new component.
  - Header: node icon/title card + search input (auto-focus) + compact `InspectorScopeToggle`.
  - Body: flat list (no group sections) of filtered rows. Each row: group chip, label (with
    `<HitHighlight>` implemented via `Text` styled runs or a small JS helper), status dots
    (`required` / `dirty`), OverrideBadge, Kbd ↵ on hover/active, then the existing
    `InspectorPropertyEditor` beneath.
  - Footer: 6-px strip with `Kbd` hints *↑↓ navigate · ↵ edit · esc close*.
  - Keyboard: handle Up/Down/Enter on the root; `activeIndex` state; `Esc` clears the query.
  - `tests/test_inspector_palette_variant.py` (new) — qtbot test that typing filters the visible rows,
    arrow keys move `activeIndex`, Enter focuses the editor.
- Deliverables: compilable variant, parity with `variants-16-20.jsx:45-142`.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest -n auto tests/test_inspector_palette_variant.py tests/test_inspector_reflection.py -q`
- Non-goals: wiring into `InspectorPane.qml` (T08), command-palette actions (V17).
- Packetization notes: → `P07`. Depends on T02 + T04. Independent of T05, T06.

### T08 Wire InspectorPane.qml to variant selector

- Goal: route `inspectorBridgeRef.property_pane_variant` into a `Loader` that picks one of the three new
  body components for the selected-node property list. Retire the legacy property-rendering block inside
  `InspectorNodeDefinitionSection.qml`; keep header + metadata + port management shared.
- Preconditions: T01 (bridge property), T02, T04, T05, T06, T07.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/shell/InspectorNodeDefinitionSection.qml` — remove the trailing
    `Repeater { model: ... selectedNodePropertyItems; delegate: InspectorPropertyEditor }` block. This
    block is now owned by the variant body.
  - `ea_node_editor/ui_qml/components/shell/InspectorPane.qml` — after
    `InspectorNodeDefinitionSection`, add a `Loader` whose `sourceComponent` is chosen by
    `switch(root.inspectorBridgeRef ? root.inspectorBridgeRef.property_pane_variant : "smart_groups")`.
    Map: `smart_groups` → `InspectorSmartGroupsBody`, `accordion_cards` →
    `InspectorAccordionCardsBody`, `palette` → `InspectorPaletteBody`. Loader must inherit
    `propertyItems: root.selectedNodePropertyItems` + `pane: root`.
  - `tests/main_window_shell/view_library_inspector.py` + `test_window_library_inspector.py` — relax
    any assertion that depends on the old property-Repeater nested inside the definition card; instead
    assert the expected variant object is present via `objectName`.
- Deliverables: live variant switching; changing the combo in Graphics Settings re-renders the pane
  on the next `inspector_state_changed`.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest -n auto tests/test_inspector_reflection.py tests/test_window_library_inspector.py tests/main_window_shell/ -q`
  - Manual smoke: select a node, flip variant in Settings three times, confirm every variant paints
    correctly in Stitch Dark and Stitch Light.
- Non-goals: `InspectorPropertyEditor` changes; new bridge APIs; annotating node specs with groups.
- Packetization notes: → `P08`. Last packet; depends on every earlier T0x.

## Work Packet Conversion Map

1. `P01 Settings rail` — derived primarily from **T01**.
2. `P02 PropertySpec group field` — derived primarily from **T02**. Independent of P01; can land first.
3. `P03 Graphics Settings combo` — derived primarily from **T03**. Depends on P01.
4. `P04 Shared inspector primitives` — derived primarily from **T04**. Independent; pure additions.
5. `P05 Smart Groups body` — derived primarily from **T05**. Depends on P02 + P04.
6. `P06 Accordion Cards body` — derived primarily from **T06**. Depends on P02 + P04.
7. `P07 Palette body` — derived primarily from **T07**. Depends on P02 + P04.
8. `P08 Wire + retire classic` — derived primarily from **T08**. Depends on everything.

A later optional `P09 Node spec group annotations` back-fills `PropertySpec.group=` on the DPF /
Compute / Source specs so Smart Groups and Accordion Cards show real Source / Selection / Post clusters
instead of a single `"Properties"` bucket. **Landed** — see "Completed follow-ups" below.

## Test Plan

- **Unit / payload:** `tests/test_app_preferences.py` (round-trip of `property_pane_variant`);
  `tests/test_window_library_inspector.py` (property items carry `group`).
- **Presenter / bridge:** `tests/test_inspector_reflection.py` — ensure `set_property_pane_variant`
  emits `inspector_state_changed` and that editing a property still round-trips to the model when the
  variant is non-default.
- **Variant-specific QML:** new qtbot tests
  `tests/test_inspector_smart_groups_variant.py`,
  `tests/test_inspector_accordion_cards_variant.py`,
  `tests/test_inspector_palette_variant.py`.
- **Integration:** `tests/main_window_shell/view_library_inspector.py` — assert every variant renders
  for a selected node under `QT_QPA_PLATFORM=offscreen`.
- **Dialog:** `tests/ui/dialogs/test_graphics_settings_dialog.py` — combo presence, round-trip.
- Run everything per packet with `.\venv\Scripts\python.exe -m pytest -n auto` (user's global rule).
- **Manual end-to-end (once per packet that changes render):** open project, select a node, toggle
  shell theme Dark ↔ Light, flip variant in Settings; verify no hardcoded colors survive the theme flip.

## Assumptions

- Design intent locked via `chats/chat1.md` + `Property Pane Variants v2.html`; no further iteration on
  V12 / V15 / V16 layouts in this plan.
- Users want to retire the current pane rather than keep a fourth "Classic" option (confirmed).
- Grouping metadata lives on `PropertySpec` as an optional string; node specs back-fill later
  (confirmed).
- Default variant = `smart_groups` — smallest behavioral delta from today's flat list (V12 degrades to a
  single "Properties" card when no groups are annotated).
- V16 Palette body does not hijack global keyboard (no new Ctrl+K binding at shell level) — its Up / Down
  / Enter are scoped to when its search input has focus. Global palette shortcuts are out of scope.
- The existing `InspectorPropertyEditor.qml` atom handles every `editor_mode` correctly; variant bodies
  only choose *layout*, never replace the editor. This keeps bridge contracts unchanged.
- No changes to `InspectorPortManagementSection` or the pin inspector; the variant only replaces the
  property-list rendering inside `InspectorNodeDefinitionSection`.
- Stitch Dark and Stitch Light tokens already cover every color the variants reference; no new theme
  tokens are introduced.

## Completed follow-ups

- **P09 — DPF Source/Selection/Post group annotations** — `dpf_output_mode_property()` factory now
  defaults to `group="Post"`, and every hand-authored DPF `PropertySpec` literal in
  `ea_node_editor/nodes/builtins/ansys_dpf_compute.py` (20 literals) and
  `ea_node_editor/nodes/builtins/ansys_dpf_helper_adapters.py` (7 literals) carries an explicit
  `group="Source"` / `"Selection"` / `"Post"`. Covered by `tests/test_dpf_property_groups.py`.

## Follow-ups (explicitly out of scope)

- Dynamic `ansys_dpf_operator_catalog.py` specs — still fall back to the `"Properties"` bucket. A
  follow-up could map by DPF operator `family_path` (`"result"` → Source, `"scoping"` → Selection,
  `"math"` / `"averaging"` → Post) if a hand-curated table is desired.
- Port the remaining Tweaks from the HTML (`showHelp`, `showOverride`, `paneWidth`) — these live on
  the design canvas harness, not the variants.
- Variants V11, V13, V14, V17–V20 from the bundle.
- Group vocabulary for non-DPF plugins (`core.py`, `hpc.py`, `integrations_*.py`, `passive_media.py`)
  — the Source / Selection / Post taxonomy is DPF-centric and doesn't map cleanly to logger / email /
  excel nodes, so those specs intentionally stay on the synthetic `"Properties"` bucket.

## Between-packet workflow (per user request)

After each packet is implemented:

1. I run `.\venv\Scripts\python.exe -m pytest -n auto` on the inspector / property-pane test targets
   listed in that packet's `Verification` block before reporting done.
2. I commit the packet's changes with a descriptive message referencing the variant and packet id.
3. I hand back the **exact resume prompt** for a fresh thread that contains: (a) the plan path,
   (b) the packet id to implement next, (c) the last commit sha, (d) an explicit instruction to open
   this plan and continue from that packet.

Example resume prompt I will give after each commit:

```
Continue from `C:\Users\emre_\PycharmProjects\EA_Node_Editor\PLANS_TO_IMPLEMENT\in_progress\property_pane_variants.md`.
I just landed P0<n> (commit <sha>). Please implement the next packet P0<n+1> end-to-end exactly as the
plan specifies, running `.\venv\Scripts\python.exe -m pytest -n auto` on every test file named in that
packet's Verification block before committing. Commit with message
"P0<n+1> <packet title> (Property Pane Variants)". After the commit, print the next resume prompt.
```
