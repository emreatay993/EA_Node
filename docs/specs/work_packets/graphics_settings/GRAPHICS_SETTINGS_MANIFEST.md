# GRAPHICS_SETTINGS Work Packet Manifest

- Date: `2026-03-12`
- Scope baseline: implement app-wide graphics settings and live shell/canvas theme selection without collapsing the current shell/controller/QML modularity.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline: `ea_node_editor/settings.py`, `ea_node_editor/ui/dialogs/workflow_settings_dialog.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui/theme/*`, `ea_node_editor/ui_qml/MainShell.qml`, and `ea_node_editor/ui_qml/components/GraphCanvas.qml` are the primary modules this packet set extends.

## Packet Order (Strict)

1. `GRAPHICS_SETTINGS_P00_bootstrap.md`
2. `GRAPHICS_SETTINGS_P01_app_preferences_foundation.md`
3. `GRAPHICS_SETTINGS_P02_settings_dialog_scaffold.md`
4. `GRAPHICS_SETTINGS_P03_graphics_settings_shell_wiring.md`
5. `GRAPHICS_SETTINGS_P04_canvas_preferences_binding.md`
6. `GRAPHICS_SETTINGS_P05_theme_registry_runtime_apply.md`
7. `GRAPHICS_SETTINGS_P06_shell_qml_theme_adoption.md`
8. `GRAPHICS_SETTINGS_P07_canvas_qml_theme_adoption.md`
9. `GRAPHICS_SETTINGS_P08_qa_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/graphics-settings/p00-bootstrap` | Save the packet set into the repo and register it in the spec index |
| P01 App Preferences Foundation | `codex/graphics-settings/p01-app-preferences-foundation` | Add versioned app-preferences defaults and controller/store scaffolding |
| P02 Settings Dialog Scaffold | `codex/graphics-settings/p02-settings-dialog-scaffold` | Extract shared settings dialog shell and add `GraphicsSettingsDialog` |
| P03 Graphics Settings Shell Wiring | `codex/graphics-settings/p03-graphics-settings-shell-wiring` | Add menu action, shell API, and app-preferences/controller composition |
| P04 Canvas Preferences Binding | `codex/graphics-settings/p04-canvas-preferences-binding` | Bind grid/minimap/snap behavior to persisted graphics preferences |
| P05 Theme Registry Runtime Apply | `codex/graphics-settings/p05-theme-registry-runtime-apply` | Add shared theme registry, runtime stylesheet apply, and QML palette bridge |
| P06 Shell QML Theme Adoption | `codex/graphics-settings/p06-shell-qml-theme-adoption` | Move shell QML surfaces onto the shared theme palette |
| P07 Canvas QML Theme Adoption | `codex/graphics-settings/p07-canvas-qml-theme-adoption` | Move canvas QML neutrals onto the shared theme palette |
| P08 QA + Traceability | `codex/graphics-settings/p08-qa-traceability` | Update requirements/traceability and run the final regression gate |

## Feature Defaults (Locked for Packet Set)

- App-wide preferences file path: `user_data_dir()/app_preferences.json`
- Preferences document shape begins with `kind="ea-node-editor/app-preferences"` and `version=1`
- Default graphics payload:
  - `canvas.show_grid = true`
  - `canvas.show_minimap = true`
  - `canvas.minimap_expanded = true`
  - `interaction.snap_to_grid = false`
  - `theme.theme_id = "stitch_dark"`
- Theme registry scope for v1: `stitch_dark`, `stitch_light`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `GRAPHICS_SETTINGS_Pxx_<name>.md`
- Implementation prompt: `GRAPHICS_SETTINGS_Pxx_<name>_PROMPT.md`
- Status ledger update in [GRAPHICS_SETTINGS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md):
  - branch label
  - commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Packet Template Rules

- Every packet spec must include: objective, preconditions, target subsystems, required behavior, non-goals, verification commands, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Do not start packet `N+1` before packet `N` is marked `PASS` in the status ledger.
- `P00` is documentation-only. `P01` through `P08` may change source/test files, but each thread must implement exactly one packet.
- Keep `ShellWindow` QML-facing slot/property names stable, including `show_workflow_settings_dialog()`, `set_script_editor_panel_visible()`, and the existing graph canvas integration contract methods.
- Reuse modular seams from `SHELL_MOD` and `QML_SURFACE_MOD`; prefer focused helper/controller/component additions over expanding monolithic files.
- App-wide graphics settings must stay out of `.sfe` project metadata and out of `last_session.json`.
- Theme adoption packets may replace hardcoded neutral shell/canvas colors, but must not change semantic node/port/edge color meaning unless their packet spec explicitly allows it.
