# ARCH_SECOND_PASS Work Packet Manifest

- Date: `2026-03-17`
- Scope baseline: second-pass targeted refactor of the shell/QML/canvas/core boundary seams that remain high-maintenance after the first modularization wave, with no intentional runtime feature changes and no repo-wide rewrite.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node Execution Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/45_NODE_EXECUTION_MODEL.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
  - [Traceability Matrix](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/TRACEABILITY_MATRIX.md)
- Runtime baseline:
  - `ea_node_editor/ui/shell/window.py` remains a 2267-line host facade with 303 defs and broad QML-facing ownership despite prior controller extraction.
  - `ea_node_editor/ui/shell/controllers/workspace_library_controller.py` is still a 900-line umbrella controller, and packet-owned controllers/helpers still reach host-private `ShellWindow` state.
  - Focused shell bridges exist, but `shell_library_bridge.py`, `shell_workspace_bridge.py`, `shell_inspector_bridge.py`, and `graph_canvas_bridge.py` still rely heavily on reflective forwarding and compatibility fallbacks.
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml` (1465 lines), `GraphNodeHost.qml` (1013), `GraphMediaPanelSurface.qml` (1143), and `components/shell/InspectorPane.qml` (1223) remain concentrated QML/UI hotspots.
  - Surface metrics and geometry logic are split across `ea_node_editor/ui_qml/graph_surface_metrics.py` and `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`, creating dual sources of truth.
  - `ea_node_editor/ui_qml/graph_scene_mutation_history.py` still mixes graph mutation, layout math, history grouping, fragment logic, and UI-facing coordination, while subnode behavior spans graph, execution, and UI layers.
  - `ea_node_editor/persistence/migration.py` still imports `normalize_passive_style_presets` from `ea_node_editor.ui.passive_style_presets`, and workspace-order ownership remains diffuse across persistence and workspace layers.
  - Verification breadth is strong, but traceability/perf docs still contain stale gate evidence and caveats, and shell/QML suites still document subprocess or fresh-process fallbacks for stability.

## Packet Order (Strict)

1. `ARCH_SECOND_PASS_P00_bootstrap.md`
2. `ARCH_SECOND_PASS_P01_shell_window_host_protocols.md`
3. `ARCH_SECOND_PASS_P02_qml_bridge_contracts.md`
4. `ARCH_SECOND_PASS_P03_graph_canvas_interaction_state.md`
5. `ARCH_SECOND_PASS_P04_graph_node_host_split.md`
6. `ARCH_SECOND_PASS_P05_surface_metrics_and_heavy_panes.md`
7. `ARCH_SECOND_PASS_P06_graph_scene_core_contracts.md`
8. `ARCH_SECOND_PASS_P07_persistence_workspace_ownership.md`
9. `ARCH_SECOND_PASS_P08_verification_traceability_hardening.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/arch-second-pass/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and record execution waves and the status ledger |
| P01 ShellWindow Host Protocols | `codex/arch-second-pass/p01-shell-window-host-protocols` | Reduce host-private controller coupling and turn `ShellWindow` into a cleaner composition root/facade |
| P02 QML Bridge Contracts | `codex/arch-second-pass/p02-qml-bridge-contracts` | Replace reflective bridge forwarding with explicit adapters and fence packet-owned QML off raw context bypasses |
| P03 GraphCanvas Interaction State | `codex/arch-second-pass/p03-graph-canvas-interaction-state` | Extract stateful interaction policy from `GraphCanvas.qml` while preserving its public integration contract |
| P04 GraphNodeHost Split | `codex/arch-second-pass/p04-graph-node-host-split` | Split `GraphNodeHost.qml` host-routing, chrome, and hit-testing concerns into focused helpers/components |
| P05 Surface Metrics And Heavy Panes | `codex/arch-second-pass/p05-surface-metrics-and-heavy-panes` | Unify surface metrics ownership and decompose `GraphMediaPanelSurface.qml` and `InspectorPane.qml` |
| P06 Graph Scene Core Contracts | `codex/arch-second-pass/p06-graph-scene-core-contracts` | Peel non-UI graph commands out of `GraphSceneMutationHistory` and isolate subnode cross-layer contracts |
| P07 Persistence Workspace Ownership | `codex/arch-second-pass/p07-persistence-workspace-ownership` | Remove persistence-to-UI leaks and give workspace-order ownership a single authoritative seam |
| P08 Verification Traceability Hardening | `codex/arch-second-pass/p08-verification-traceability-hardening` | Refresh stale QA evidence/caveats and add automated validation for the traceability/proof layer |

## Locked Defaults

- Preserve current user-visible behavior and current public QML/object contracts unless a packet explicitly changes one.
- Keep `MainShell.qml` as the shell composition root and keep `GraphCanvas.qml` root contracts stable: `objectName: "graphCanvas"`, `toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, and `performLibraryDrop()`.
- Keep `GraphSceneBridge` public `@pyqtSlot` and `@pyqtProperty` names stable through this packet set; refactors should happen behind the current bridge surface unless a packet explicitly widens scope.
- Keep raw context properties (`mainWindow`, `sceneBridge`, `viewBridge`, `workspaceTabsBridge`, `consoleBridge`, and related compatibility seams) available until `P08`, but do not treat them as the preferred ownership path for packet-owned QML consumers.
- Do not introduce `.sfe`, session, or app-preferences schema-version changes in this packet set unless a packet explicitly requires a narrow migration-safe adjustment.
- Prefer new focused helpers/services/modules over adding more responsibilities to `ShellWindow`, `GraphCanvas.qml`, `GraphNodeHost.qml`, or `GraphSceneBridge`.
- Use the project venv for verification commands: `./venv/Scripts/python.exe`.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

### Wave 4
- `P04`

### Wave 5
- `P05`
- `P06`

### Wave 6
- `P07`

### Wave 7
- `P08`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `ARCH_SECOND_PASS_Pxx_<name>.md`
- Implementation prompt: `ARCH_SECOND_PASS_Pxx_<name>_PROMPT.md`
- Status ledger update in [ARCH_SECOND_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_STATUS.md):
  - branch label
  - accepted commit sha
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement ARCH_SECOND_PASS_PXX_<name>.md exactly. Before editing, read ARCH_SECOND_PASS_MANIFEST.md, ARCH_SECOND_PASS_STATUS.md, and ARCH_SECOND_PASS_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, update ARCH_SECOND_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P08` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
