# GRAPH_SURFACE_INPUT Work Packet Manifest

- Date: `2026-03-16`
- Scope baseline: establish a durable host/surface input-routing architecture so embedded controls inside graph nodes do not lose left-click ownership to the full-card drag overlay, while preserving current body drag/select/context behavior.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node SDK](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml` still places the full-card drag `MouseArea` above surface content.
  - `GraphNodeSurfaceLoader.qml` currently forwards `blocksHostInteraction` and `hoverActionHitRect`, but not a general embedded-control contract.
  - `GraphInlinePropertiesLayer.qml` supports `toggle`, `enum`, `text`, and `number`, but not `textarea` or `path`.
  - `GraphMediaPanelSurface.qml` uses the host hover proxy for its crop button and keeps its own crop-mode whole-surface lock.

## Packet Order (Strict)

1. `GRAPH_SURFACE_INPUT_P00_bootstrap.md`
2. `GRAPH_SURFACE_INPUT_P01_host_drag_layer_foundation.md`
3. `GRAPH_SURFACE_INPUT_P02_surface_input_contract.md`
4. `GRAPH_SURFACE_INPUT_P03_interaction_bridge.md`
5. `GRAPH_SURFACE_INPUT_P04_shared_surface_controls.md`
6. `GRAPH_SURFACE_INPUT_P05_inline_core_editors.md`
7. `GRAPH_SURFACE_INPUT_P06_inline_extended_editors.md`
8. `GRAPH_SURFACE_INPUT_P07_media_surface_migration.md`
9. `GRAPH_SURFACE_INPUT_P08_pointer_regression_audit.md`
10. `GRAPH_SURFACE_INPUT_P09_docs_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/graph-surface-input/p00-bootstrap` | Save the packet set into the repo and register it in the spec index |
| P01 Host Drag Layer Foundation | `codex/graph-surface-input/p01-host-drag-layer-foundation` | Move host drag/select handling under surface content without changing public graph contracts |
| P02 Surface Input Contract | `codex/graph-surface-input/p02-surface-input-contract` | Add `embeddedInteractiveRects` and host hit-testing for local control ownership |
| P03 Interaction Bridge | `codex/graph-surface-input/p03-interaction-bridge` | Route inline commits and browse actions by explicit `nodeId` instead of selected-node state |
| P04 Shared Surface Controls | `codex/graph-surface-input/p04-shared-surface-controls` | Add reusable graph-surface control components and host-space rect helpers |
| P05 Inline Core Editors | `codex/graph-surface-input/p05-inline-core-editors` | Migrate inline toggle/enum/text/number editors onto the shared control kit |
| P06 Inline Extended Editors | `codex/graph-surface-input/p06-inline-extended-editors` | Add inline `textarea` and `path` editors with graph-surface-safe commit/browse behavior |
| P07 Media Surface Migration | `codex/graph-surface-input/p07-media-surface-migration` | Remove the hover proxy and migrate media-surface buttons to direct surface ownership |
| P08 Pointer Regression Audit | `codex/graph-surface-input/p08-pointer-regression-audit` | Audit all graph-surface interactive regions, add pointer regression helpers, and freeze the pattern |
| P09 Docs Traceability | `codex/graph-surface-input/p09-docs-traceability` | Close docs, TODOs, QA matrix, and traceability for the packet set |

## Locked Defaults

- `blocksHostInteraction` remains the whole-surface modal lock for tools such as crop mode. It must not be reused for ordinary inline controls.
- `embeddedInteractiveRects` is the local control-ownership contract. Its coordinates are in host-local space and represent regions where host body drag/select/open/context behavior must yield.
- `hoverActionHitRect` and `graphNodeSurfaceHoverActionButton` are compatibility-only shims through `P06`. `P07` removes them.
- Hover-only affordances should use `HoverHandler` or `MouseArea { acceptedButtons: Qt.NoButton }` rather than an invisible click-swallowing overlay.
- Shared graph-surface controls live under `ea_node_editor/ui_qml/components/graph/surface_controls/`. Reuse them instead of embedding custom button/field implementations in each surface.
- Inline editor support on graph surfaces after `P06` is locked to: `toggle`, `enum`, `text`, `number`, `textarea`, and `path`.
- Inline `path` editors browse through `window.py::browse_node_property_path(nodeId, key, current_path)` and do not depend on selected-node state.
- Inline `textarea` editors follow the inspector commit model: explicit dirty state, `Ctrl+Enter` commit, `Esc` reset, and no implicit node drag while focused.

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `GRAPH_SURFACE_INPUT_Pxx_<name>.md`
- Implementation prompt: `GRAPH_SURFACE_INPUT_Pxx_<name>_PROMPT.md`
- Status ledger update in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md):
  - branch label
  - commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement GRAPH_SURFACE_INPUT_PXX_<name>.md exactly. Before editing, read GRAPH_SURFACE_INPUT_MANIFEST.md, GRAPH_SURFACE_INPUT_STATUS.md, and GRAPH_SURFACE_INPUT_PXX_<name>.md. Implement only PXX. Preserve public QML/object contracts unless the packet explicitly introduces or removes one. Update GRAPH_SURFACE_INPUT_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks. Stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every packet spec must include: objective, preconditions, target subsystems, required behavior, non-goals, verification commands, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the exact standard thread prompt shell defined above.
- Do not start packet `N+1` before packet `N` is marked `PASS` in the status ledger.
- `P00` is documentation-only. `P01` through `P09` may change source/test files, but each thread must implement exactly one packet.
- Keep `graphNodeCard`, `graphCanvas`, existing port object names, and current public `GraphCanvas` methods stable unless a packet explicitly removes a private compatibility shim.
- Reuse modular seams introduced by `PASSIVE_NODES`, `QML_SURFACE_MOD`, and `GRAPH_UX` instead of reopening monolithic QML files without extraction.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly says otherwise.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files.
