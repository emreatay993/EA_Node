# QML_SURFACE_MOD Work Packet Manifest

- Date: `2026-03-10`
- Scope baseline: behavior-preserving modular refactor of the full QML shell surface (`MainShell.qml` + `GraphCanvas.qml`) with no intentional UX/runtime changes.
- Canonical requirements: [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [QA + Acceptance](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline: `ea_node_editor/ui_qml/MainShell.qml` and `ea_node_editor/ui_qml/components/GraphCanvas.qml` are the primary large modules targeted by this packet set.

## Packet Order (Strict)

1. `QML_SURFACE_MOD_P00_bootstrap.md`
2. `QML_SURFACE_MOD_P01_shell_primitives.md`
3. `QML_SURFACE_MOD_P02_shell_chrome.md`
4. `QML_SURFACE_MOD_P03_shell_library_pane.md`
5. `QML_SURFACE_MOD_P04_shell_workspace_center.md`
6. `QML_SURFACE_MOD_P05_shell_inspector.md`
7. `QML_SURFACE_MOD_P06_shell_overlays.md`
8. `QML_SURFACE_MOD_P07_graph_canvas_utils.md`
9. `QML_SURFACE_MOD_P08_graph_canvas_layers.md`
10. `QML_SURFACE_MOD_P09_graph_canvas_interactions_regression.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/qml-surface-mod/p00-bootstrap` | Save the packet set into the repo and register it in the spec index |
| P01 Shell Primitives | `codex/qml-surface-mod/p01-shell-primitives` | Extract shared shell primitives/helpers from `MainShell.qml` |
| P02 Shell Chrome | `codex/qml-surface-mod/p02-shell-chrome` | Extract title bar, run toolbar, and status strip |
| P03 Shell Library Pane | `codex/qml-surface-mod/p03-shell-library-pane` | Extract node library pane and workflow context popup/backdrop |
| P04 Shell Workspace Center | `codex/qml-surface-mod/p04-shell-workspace-center` | Extract workspace/view/scope center composition |
| P05 Shell Inspector | `codex/qml-surface-mod/p05-shell-inspector` | Extract inspector panel editors and payload bindings |
| P06 Shell Overlays | `codex/qml-surface-mod/p06-shell-overlays` | Extract graph-search, script-editor, and graph-hint overlays |
| P07 GraphCanvas Utils | `codex/qml-surface-mod/p07-graph-canvas-utils` | Extract pure GraphCanvas helper logic into JS module(s) |
| P08 GraphCanvas Layers | `codex/qml-surface-mod/p08-graph-canvas-layers` | Extract GraphCanvas background/grid and drop-preview layers |
| P09 GraphCanvas Interactions Regression | `codex/qml-surface-mod/p09-graph-canvas-interactions-regression` | Extract minimap/context/input overlays and run final regression gate |

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `QML_SURFACE_MOD_Pxx_<name>.md`
- Implementation prompt: `QML_SURFACE_MOD_Pxx_<name>_PROMPT.md`
- Status ledger update in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md):
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
- Keep Python to QML context property names stable (`mainWindow`, `sceneBridge`, `viewBridge`, `consoleBridge`, `scriptEditorBridge`, `scriptHighlighterBridge`, `workspaceTabsBridge`, and status bridges).
- Keep QML object and method contracts relied on by tests stable (`libraryPane`, `graphHintOverlay`, `graphCanvas`, `minimapExpanded`, `toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, `performLibraryDrop()`).
- Prefer composition components and JS helper modules over large monolithic QML files while preserving runtime behavior.
