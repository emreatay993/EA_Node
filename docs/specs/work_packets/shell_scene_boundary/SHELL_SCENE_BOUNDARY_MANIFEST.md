# SHELL_SCENE_BOUNDARY Work Packet Manifest

- Date: `2026-03-17`
- Scope baseline: behavior-preserving refactor of the shell/scene/application orchestration boundary so `ShellWindow` and `GraphSceneBridge` stop acting as monolithic QML-facing god objects, QML stops depending directly on raw app bridges for owned concerns, and the small `settings.py` UI dependency leak is removed without intentionally changing runtime behavior.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/ui/shell/window.py` is 2296 lines and still owns QML host bootstrap, a large QML-facing slot/property surface, graphics/session glue, and several UI-only helper flows.
  - `ea_node_editor/ui_qml/graph_scene_bridge.py` is 1905 lines and mixes workspace binding, scope/selection state, graph mutations, layout/history grouping, payload building, theme resolution, and PDF media normalization.
  - `ea_node_editor/ui_qml/MainShell.qml` and `ea_node_editor/ui_qml/components/GraphCanvas.qml` still depend on raw app bridges/context properties (`mainWindow`, `sceneBridge`, `viewBridge`, `workspaceTabsBridge`, `consoleBridge`, and related pass-throughs) instead of focused orchestration facades.
  - `ea_node_editor/settings.py` imports `DEFAULT_GRAPH_THEME_ID` from `ea_node_editor.ui.graph_theme`, which pulls a UI dependency into the defaults/persistence layer.
  - `SHELL_MOD` and `QML_SURFACE_MOD` already extracted visual/component structure, but they did not complete shell/scene/QML boundary ownership cleanup.
  - Baseline regression note: `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -k passive_image_panel_properties_and_size -q` currently fails because passive image-panel round-trips add default `crop_x`, `crop_y`, `crop_w`, and `crop_h` fields. This packet set must treat that failure as out-of-scope baseline context unless a packet explicitly widens into persistence repair.

## Packet Order (Strict)

1. `SHELL_SCENE_BOUNDARY_P00_bootstrap.md`
2. `SHELL_SCENE_BOUNDARY_P01_settings_defaults_boundary.md`
3. `SHELL_SCENE_BOUNDARY_P02_qml_context_bootstrap.md`
4. `SHELL_SCENE_BOUNDARY_P03_shell_library_search_bridge.md`
5. `SHELL_SCENE_BOUNDARY_P04_shell_workspace_run_bridge.md`
6. `SHELL_SCENE_BOUNDARY_P05_shell_inspector_bridge.md`
7. `SHELL_SCENE_BOUNDARY_P06_graph_canvas_boundary_bridge.md`
8. `SHELL_SCENE_BOUNDARY_P07_graph_scene_scope_selection_split.md`
9. `SHELL_SCENE_BOUNDARY_P08_graph_scene_mutation_history_split.md`
10. `SHELL_SCENE_BOUNDARY_P09_graph_scene_payload_builder_split.md`
11. `SHELL_SCENE_BOUNDARY_P10_boundary_regression_docs.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/shell-scene-boundary/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and record the execution waves/status ledger |
| P01 Settings Defaults Boundary | `codex/shell-scene-boundary/p01-settings-defaults-boundary` | Remove the UI-layer import leak from `settings.py` while preserving graphics/app-preferences defaults |
| P02 QML Context Bootstrap | `codex/shell-scene-boundary/p02-qml-context-bootstrap` | Extract QML host/context registration and create narrow facade skeletons for later packets |
| P03 Shell Library Search Bridge | `codex/shell-scene-boundary/p03-shell-library-search-bridge` | Move library/search/quick-insert/hint QML consumers onto a focused shell bridge |
| P04 Shell Workspace Run Bridge | `codex/shell-scene-boundary/p04-shell-workspace-run-bridge` | Move workspace/run/title/console QML consumers onto a focused workspace bridge |
| P05 Shell Inspector Bridge | `codex/shell-scene-boundary/p05-shell-inspector-bridge` | Move inspector QML consumers onto a focused inspector bridge |
| P06 GraphCanvas Boundary Bridge | `codex/shell-scene-boundary/p06-graph-canvas-boundary-bridge` | Replace GraphCanvas direct raw-bridge dependency with dedicated canvas boundary adapters |
| P07 GraphScene Scope Selection Split | `codex/shell-scene-boundary/p07-graph-scene-scope-selection-split` | Extract workspace binding, scope, selection, and bounds behavior from `GraphSceneBridge` |
| P08 GraphScene Mutation History Split | `codex/shell-scene-boundary/p08-graph-scene-mutation-history-split` | Extract mutation/layout/history/fragment behavior from `GraphSceneBridge` |
| P09 GraphScene Payload Builder Split | `codex/shell-scene-boundary/p09-graph-scene-payload-builder-split` | Extract payload/theme/minimap/media normalization building from `GraphSceneBridge` |
| P10 Boundary Regression Docs | `codex/shell-scene-boundary/p10-boundary-regression-docs` | Run the combined boundary regression slice and close architecture/traceability/QA docs |

## Locked Defaults

- Preserve current user-visible shell/canvas behavior and existing public contracts unless a packet explicitly changes one.
- Keep these context properties available until `P10` verifies the new facades cover all QML consumers: `mainWindow`, `sceneBridge`, `viewBridge`, `consoleBridge`, `scriptEditorBridge`, `scriptHighlighterBridge`, `themeBridge`, `graphThemeBridge`, `workspaceTabsBridge`, `uiIcons`, `statusEngine`, `statusJobs`, `statusMetrics`, and `statusNotifications`.
- Keep `GraphCanvas.qml` root contracts stable: `objectName: "graphCanvas"`, `toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, and `performLibraryDrop()`.
- Keep `GraphSceneBridge` public `@pyqtSlot` / `@pyqtProperty` names stable across `P07` through `P09`; those packets refactor internals behind the existing contract.
- Reuse seams introduced by `SHELL_MOD`, `QML_SURFACE_MOD`, and `GRAPH_SURFACE_INPUT` instead of reopening visual/component extraction work.
- Do not introduce schema-version changes or intentional `.sfe` / app-preferences document-shape changes in this packet set.
- Treat the serializer image-panel crop-field regression as baseline-only context; do not sweep persistence fixes into these packets unless the packet spec explicitly says so.
- Prefer new facade/helper modules over adding more QML-facing slots/properties to `ShellWindow` or more responsibilities to `GraphSceneBridge`.

## Execution Waves

### Wave 1
- `P01`
- `P02`

### Wave 2
- `P03`
- `P04`
- `P05`

### Wave 3
- `P06`

### Wave 4
- `P07`

### Wave 5
- `P08`

### Wave 6
- `P09`

### Wave 7
- `P10`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `SHELL_SCENE_BOUNDARY_Pxx_<name>.md`
- Implementation prompt: `SHELL_SCENE_BOUNDARY_Pxx_<name>_PROMPT.md`
- Status ledger update in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md):
  - branch label
  - commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement SHELL_SCENE_BOUNDARY_PXX_<name>.md exactly. Before editing, read SHELL_SCENE_BOUNDARY_MANIFEST.md, SHELL_SCENE_BOUNDARY_STATUS.md, and SHELL_SCENE_BOUNDARY_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, update SHELL_SCENE_BOUNDARY_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P10` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
