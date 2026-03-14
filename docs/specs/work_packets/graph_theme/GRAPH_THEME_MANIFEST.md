# GRAPH_THEME Work Packet Manifest

- Date: `2026-03-14`
- Scope baseline: introduce a dedicated app-wide node/edge graph theme pipeline plus a custom graph-theme library/editor without bloating the existing shell theme, graph-model, or QML surface modules.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline: the `GRAPHICS_SETTINGS` packet set already provides app-wide graphics preferences, shell/canvas theme selection, the shared shell theme registry in `ea_node_editor/ui/theme/*`, and `ThemeBridge` for shell/canvas chrome. Graph node/edge visuals still depend on a mix of `themeBridge.palette` and hardcoded presenter/QML color helpers in `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/components/graph/NodeCard.qml`, and `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`.

## Packet Order (Strict)

1. `GRAPH_THEME_P00_bootstrap.md`
2. `GRAPH_THEME_P01_graph_theme_foundation.md`
3. `GRAPH_THEME_P02_runtime_resolution_bridge.md`
4. `GRAPH_THEME_P03_graph_payload_theme_pipeline.md`
5. `GRAPH_THEME_P04_graph_qml_theme_adoption.md`
6. `GRAPH_THEME_P05_graph_theme_settings_controls.md`
7. `GRAPH_THEME_P06_custom_theme_library.md`
8. `GRAPH_THEME_P07_graph_theme_editor_shell.md`
9. `GRAPH_THEME_P08_custom_theme_editing_live_apply.md`
10. `GRAPH_THEME_P09_qa_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/graph-theme/p00-bootstrap` | Save the packet set into the repo and register it in the spec index |
| P01 Graph Theme Foundation | `codex/graph-theme/p01-graph-theme-foundation` | Add graph-theme domain types, built-in registry, shell-to-graph defaults, and app-preferences v2 scaffolding |
| P02 Runtime Resolution Bridge | `codex/graph-theme/p02-runtime-resolution-bridge` | Resolve the active graph theme at runtime and expose `graphThemeBridge` to QML |
| P03 Graph Payload Theme Pipeline | `codex/graph-theme/p03-graph-payload-theme-pipeline` | Move node accent and edge color semantics into the graph-theme presentation path |
| P04 Graph QML Theme Adoption | `codex/graph-theme/p04-graph-qml-theme-adoption` | Move `NodeCard.qml` and `EdgeLayer.qml` onto `graphThemeBridge` |
| P05 Graph Theme Settings Controls | `codex/graph-theme/p05-graph-theme-settings-controls` | Add app-wide follow-shell and explicit graph-theme selection controls |
| P06 Custom Theme Library | `codex/graph-theme/p06-custom-theme-library` | Add custom-theme normalization, persistence, CRUD helpers, and registry overlay |
| P07 Graph Theme Editor Shell | `codex/graph-theme/p07-graph-theme-editor-shell` | Add graph-theme manager/editor dialog shell and library-management UI wiring |
| P08 Custom Theme Editing + Live Apply | `codex/graph-theme/p08-custom-theme-editing-live-apply` | Enable full custom graph-theme editing and live runtime apply |
| P09 QA + Traceability | `codex/graph-theme/p09-qa-traceability` | Update docs/traceability and close the roadmap with the final regression gate |

## Feature Defaults (Locked for Packet Set)

- Graph theme scope is app-wide only.
- No graph-theme state may be persisted into `.sfe`, project metadata, workspace metadata, or `last_session.json`.
- Shell theme ids remain `stitch_dark` and `stitch_light`.
- Built-in graph theme ids are `graph_stitch_dark` and `graph_stitch_light`.
- Default app-preferences graph-theme payload:
  - `follow_shell_theme = true`
  - `selected_theme_id = "graph_stitch_dark"`
  - `custom_themes = []`
- Graph themes affect node and edge visuals only.
- Canvas chrome such as background, grid, minimap chrome, marquee, and drop-preview chrome remains on the existing shell theme path.
- Built-in graph themes are read-only.
- Custom graph themes are stored inline in app preferences, not in external files.
- Custom theme ids use `custom_graph_theme_<8hex>`.
- New graph-theme implementation code lives under `ea_node_editor/ui/graph_theme/*`.
- The new QML-facing bridge is `graphThemeBridge`; the existing `ThemeBridge` remains the shell/canvas chrome palette surface.

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `GRAPH_THEME_Pxx_<name>.md`
- Implementation prompt: `GRAPH_THEME_Pxx_<name>_PROMPT.md`
- Status ledger update in [GRAPH_THEME_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_theme/GRAPH_THEME_STATUS.md):
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
- `P00` is documentation-only. `P01` through `P09` may change source/test files, but each thread must implement exactly one packet.
- Keep QML-facing public object/property/slot names stable unless a packet explicitly introduces a new one.
- Reuse modular seams from `SHELL_MOD`, `QML_SURFACE_MOD`, and `GRAPHICS_SETTINGS`; prefer focused helper/controller/component additions over expanding monolithic files.
- Keep shell/chrome theming in `ea_node_editor/ui/theme/*` and `ThemeBridge`; graph theming must be implemented in the new `ea_node_editor/ui/graph_theme/*` package and `graphThemeBridge`.
- Keep graph-theme shaping in the presenter/bridge layer rather than adding theme state to graph-model dataclasses or `.sfe` persistence.
