# Tooltip Manager Tiers QA Matrix

- Updated: `2026-05-17`
- Packet set: retained `TOOLTIP_MANAGER_TIERS` (`P01` through `P06`)
- Scope: final closeout matrix for the shipped app-wide tiered tooltip policy, category preference persistence, Graphics Settings controls, View menu `general` synchronization, shell/QML bridge projection, shared QML tooltip helper adoption, first-wave tutorial/warning/inactive/advanced classification, source guardrails, and traceability/docs evidence.

## Locked Scope

- `graphics.shell.tooltip_categories` is the canonical app-preference model for user-selectable tooltip visibility. The tiered manager does not persist or reload a separate `graphics.shell.show_tooltips` boolean and does not expand `.cxproj` project persistence.
- Configurable categories are `general`, `tutorial`, `advanced`, `warning`, and `inactive`; defaults are `general=true`, `tutorial=true`, `advanced=false`, `warning=true`, and `inactive=true`.
- `critical` is a registered non-configurable category. It is always effectively visible for non-empty blocker or safety copy and is not persisted as a user-disabled category.
- `View > General Help Tooltips` remains the user-facing menu action for ordinary help and maps only to `graphics.shell.tooltip_categories.general`.
- Category gating is category-only: each configurable category follows only its own flag, unknown categories normalize out of persisted preferences, and unknown runtime category queries resolve hidden.
- QML tooltip-bearing surfaces use `TooltipPolicy.js` and `ManagedToolTip.qml` for category-aware visibility. `ManagedToolTip.qml` defaults to plain text; trusted app-authored rich or styled text requires explicit opt-in and source-level guardrail coverage.
- Qt widget tooltip surfaces remain on the existing general tooltip policy path unless a future packet adds category metadata for widget-only tutorial, warning, inactive, advanced, or rich tooltip copy.

## Accepted Packet Summary

| Packet | Branch / Commit | Accepted Artifacts | Residual Risks Carried Forward |
|---|---|---|---|
| `P01` Policy Schema and Manager Contract | `codex/tooltip-manager-tiers/p01-policy-schema-and-manager-contract` / `161a7a511e3995f581f9336e313e493683477f36` | `docs/specs/work_packets/tooltip_manager_tiers/P01_policy_schema_and_manager_contract_WRAPUP.md`; `ea_node_editor/ui/shell/tooltip_policy.py`; `ea_node_editor/ui/shell/tooltip_manager.py`; `tests/test_graphics_settings_preferences.py` | Settings UI controls and QML bridge/surface adoption were intentionally deferred to P02-P04. |
| `P02` Shell State and QML Bridge Contract | `codex/tooltip-manager-tiers/p02-shell-state-and-qml-bridge-contract` / `470a0ee85e035af69b8dfe617fdb603af18c1c85` | `docs/specs/work_packets/tooltip_manager_tiers/P02_shell_state_and_qml_bridge_contract_WRAPUP.md`; shell state/controller projection; QML bridge/state bridge contract tests | User-facing settings controls were deferred to P03; shared QML helper adoption and surface migration were deferred to P04. |
| `P03` Settings UI and User Controls | `codex/tooltip-manager-tiers/p03-settings-ui-and-user-controls` / `aafdd6ca0e86c4998a04ae5ec690b65bdce4b0ec` | `docs/specs/work_packets/tooltip_manager_tiers/P03_settings_ui_and_user_controls_WRAPUP.md`; `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`; `ea_node_editor/ui/shell/host_presenter.py`; tooltip dialog/preference/shell tests | Shared QML helper migration remained P04-owned; tutorial/warning copy classification remained P05-owned. |
| `P04` QML Helper and Surface Migration | `codex/tooltip-manager-tiers/p04-qml-helper-and-surface-migration` / `d7378e090470c2d9bd2e447826f010a65f0661ac` | `docs/specs/work_packets/tooltip_manager_tiers/P04_qml_helper_and_surface_migration_WRAPUP.md`; `ea_node_editor/ui_qml/components/common/ManagedToolTip.qml`; `ea_node_editor/ui_qml/components/common/TooltipPolicy.js`; migrated P04 QML tooltip surfaces; bridge/QML/rendering/passive-surface tests | Broader copy classification, tutorial/warning coverage, and rich/styled opt-in review remained P05-owned. |
| `P05` Catalog Rollout and Tutorial/Warning Copy | `codex/tooltip-manager-tiers/p05-catalog-rollout-and-tutorial-warning-copy` / `762ad6221c1fec80938d2f90f1efa1d559b17252` | `docs/specs/work_packets/tooltip_manager_tiers/P05_catalog_rollout_and_tutorial_warning_copy_WRAPUP.md`; planned-scope QML category rollout; source guardrails; bridge boundary and QML binding tests | Qt widget tooltip surfaces remain on the general policy path because the P05 planned scope found no tutorial, warning, inactive, advanced, or rich widget tooltip copy. |

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| Tooltip category defaults, normalization, persistence round-trip, manager visibility, unknown-category handling, and critical non-disableability | `P01` | `REQ-UI-045`, `AC-REQ-UI-045-01`, `REQ-QA-047` | `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py --ignore=venv -q` | Accepted `P01` packet commit `161a7a511e3995f581f9336e313e493683477f36` |
| Focused tooltip preference and manager policy regression slice | `P01` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py -k tooltip --ignore=venv -q` | Accepted `P01` packet commit `161a7a511e3995f581f9336e313e493683477f36` |
| Shell state, controller persistence, workspace presenter, QML bridge, and support contracts | `P02` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/bridge_support.py --ignore=venv -q` | Accepted `P02` packet commit `470a0ee85e035af69b8dfe617fdb603af18c1c85` |
| QML preference binding and rendering projection for tooltip categories | `P02` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py tests/graph_track_b/qml_preference_rendering_suite.py --ignore=venv -q` | Accepted `P02` packet commit `470a0ee85e035af69b8dfe617fdb603af18c1c85` |
| Graphics tooltip preference preservation after bridge projection | `P02` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py -k tooltip --ignore=venv -q` | Accepted `P02` packet commit `470a0ee85e035af69b8dfe617fdb603af18c1c85` |
| Tooltip bridge review gate | `P02` | `REQ-UI-045`, `REQ-QA-047` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py -k tooltip --ignore=venv -q` | Accepted `P02` packet commit `470a0ee85e035af69b8dfe617fdb603af18c1c85` |
| Graphics Settings tooltip category controls and dialog value projection | `P03` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_dialog.py --ignore=venv -q` | Accepted `P03` packet commit `aafdd6ca0e86c4998a04ae5ec690b65bdce4b0ec` |
| Tooltip category app-preference persistence with settings dialog changes | `P03` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py -k tooltip --ignore=venv -q` | Accepted `P03` packet commit `aafdd6ca0e86c4998a04ae5ec690b65bdce4b0ec` |
| Shell menu/general-category synchronization after settings acceptance | `P03` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py -k tooltip --ignore=venv -q` | Accepted `P03` packet commit `aafdd6ca0e86c4998a04ae5ec690b65bdce4b0ec` |
| Tooltip settings review gate | `P03` | `REQ-UI-045`, `REQ-QA-047` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_dialog.py -k tooltip --ignore=venv -q` | Accepted `P03` packet commit `aafdd6ca0e86c4998a04ae5ec690b65bdce4b0ec` |
| Shared QML helper and migrated tooltip surfaces source-contract coverage | `P04` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q` | Accepted `P04` packet commit `d7378e090470c2d9bd2e447826f010a65f0661ac` |
| QML tooltip category binding, helper projection, and plain-text rendering coverage | `P04` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py tests/graph_track_b/qml_preference_rendering_suite.py --ignore=venv -q` | Accepted `P04` packet commit `d7378e090470c2d9bd2e447826f010a65f0661ac` |
| Graph-surface input and passive surface coverage after helper migration | `P04` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v` | Accepted `P04` packet commit `d7378e090470c2d9bd2e447826f010a65f0661ac` |
| Tooltip helper review gate | `P04` | `REQ-UI-045`, `REQ-QA-047` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py -k tooltip --ignore=venv -q` | Accepted `P04` packet commit `d7378e090470c2d9bd2e447826f010a65f0661ac` |
| Category rollout, raw-tooltip bypass prevention, and rich/styled tooltip guardrails | `P05` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_theme_editor_dialog.py --ignore=venv -q` | Accepted `P05` packet commit `762ad6221c1fec80938d2f90f1efa1d559b17252` |
| Graphics Settings tooltip controls stay aligned after catalog classification | `P05` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_dialog.py -k tooltip --ignore=venv -q` | Accepted `P05` packet commit `762ad6221c1fec80938d2f90f1efa1d559b17252` |
| Independent tutorial and warning category projection | `P05` | `REQ-UI-045`, `AC-REQ-UI-045-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py -k tooltip --ignore=venv -q` | Accepted `P05` packet commit `762ad6221c1fec80938d2f90f1efa1d559b17252` |
| Tooltip catalog review gate | `P05` | `REQ-UI-045`, `REQ-QA-047` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py -k tooltip --ignore=venv -q` | Accepted `P05` packet commit `762ad6221c1fec80938d2f90f1efa1d559b17252` |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `.\venv\Scripts\python.exe .\scripts\check_traceability.py` | Packet-owned requirement, traceability, QA matrix, and closeout proof audit |
| `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | Packet-owned markdown link validation for the requirements, index, QA matrix, status ledger, and wrap-up docs |
| `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | Review gate for P06 docs closeout |

## 2026-05-17 Execution Results

| Command | Result | Notes |
|---|---|---|
| `.\venv\Scripts\python.exe .\scripts\check_traceability.py` | PASS | Traceability audit passed after adding `REQ-UI-045`, `AC-REQ-UI-045-01`, `REQ-QA-047`, `AC-REQ-QA-047-01`, this matrix, and the spec-index registration |
| `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | PASS | Markdown link validation passed for the updated requirements, traceability matrix, spec index, and retained QA matrix |
| `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | PASS | Review gate passed for the P06 docs closeout |

## Remaining Manual Smoke Checks

1. Preference persistence: start a desktop Qt session with a clean app-preferences state, open `Settings > Graphics Settings > Layout > Tooltips`, confirm the default category states, change each configurable category, accept, relaunch, and confirm the same category map is restored without changing any `.cxproj` project file.
2. View menu synchronization: toggle `View > General Help Tooltips`, reopen Graphics Settings, and confirm only the `General help tooltips` checkbox changes while `Tutorial`, `Advanced`, `Warnings`, and `Inactive explanations` retain their prior states.
3. Independent category visibility: disable `General` while keeping `Tutorial`, `Warnings`, and `Inactive explanations` enabled, then hover graph search, minimap, tab-create, add-port, delete-port, ungroup, and inactive-port surfaces to confirm the expected non-general copy remains visible.
4. Critical non-suppression: disable every configurable tooltip category and confirm blocker or safety copy classified as `critical` still appears when the underlying surface has non-empty critical text.
5. Shared helper desktop check: on a real Windows desktop compositor, hover migrated QML controls across both shell themes and confirm tooltip text, delay, wrapping, and plain-text rendering remain coherent after category changes.

## Residual Desktop-Only Validation

- Automated coverage validates the policy, source contracts, and QML bindings offscreen, but desktop hover timing, final rasterization, high-DPI wrapping, and native compositor behavior still need manual review before a release sign-off.
- The first-wave tutorial and warning classification covers current planned-scope QML surfaces. Future tooltip-bearing QML additions must keep using the shared helper and supply an explicit reviewed category.
- Qt widget tooltip surfaces stay on the general policy path because no current widget-only tutorial, warning, inactive, advanced, or rich tooltip copy was found in the packet scope.

## Residual Risks

- Later work that introduces new tooltip categories, widget-level category metadata, or trusted rich/styled tooltip rendering must update `tooltip_policy.py`, `ManagedToolTip.qml`, guardrail tests, this matrix, and the traceability rows together.
- The old v1 global toggle contract is intentionally narrowed to the `general` category. Any future feature that expects one master user suppressor for all non-critical help must define that as a new product requirement instead of reusing `graphics.shell.show_tooltips`.
- Manual desktop checks remain recommended for perceived visual quality and hover ergonomics even though P01-P05 automated evidence covers the functional category policy.
