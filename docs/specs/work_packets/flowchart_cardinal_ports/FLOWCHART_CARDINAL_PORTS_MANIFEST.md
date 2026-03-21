# FLOWCHART_CARDINAL_PORTS Work Packet Manifest

- Date: `2026-03-21`
- Scope baseline: replace passive flowchart nodes' inconsistent 1-3 fixed-direction ports and row-band anchor math with 4 stored cardinal neutral ports, gesture-ordered flow direction, exact silhouette perimeter anchors, and updated quick-insert/drop-connect behavior, while leaving non-flowchart node wiring unchanged.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node SDK](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [Node Execution Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/45_NODE_EXECUTION_MODEL.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/nodes/types.py` only accepts `PortDirection` values `in` and `out`, and registry validation rejects any other direction token.
  - `ea_node_editor/nodes/builtins/passive_flowchart.py` still defines passive flowchart nodes with legacy keys such as `flow_in`, `flow_out`, and `branch_a` / `branch_b`, so visible handle count varies by shape.
  - `ea_node_editor/ui_qml/graph_surface_metrics.py` and `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js` still place flowchart ports through a left/right row band, which causes database/input-output side drift and prevents fixed top/bottom anchors.
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`, `ea_node_editor/ui/shell/window_library_inspector.py`, and `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py` still assume `source_direction` is a fixed `in` / `out` value.

## Packet Order (Strict)

1. `FLOWCHART_CARDINAL_PORTS_P00_bootstrap.md`
2. `FLOWCHART_CARDINAL_PORTS_P01_neutral_port_contract.md`
3. `FLOWCHART_CARDINAL_PORTS_P02_cardinal_anchor_geometry.md`
4. `FLOWCHART_CARDINAL_PORTS_P03_canvas_neutral_interaction.md`
5. `FLOWCHART_CARDINAL_PORTS_P04_flowchart_drop_connect_insert.md`
6. `FLOWCHART_CARDINAL_PORTS_P05_regression_docs_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/flowchart-cardinal-ports/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Neutral Port Contract | `codex/flowchart-cardinal-ports/p01-neutral-port-contract` | Add the neutral flowchart port contract, migrate the built-in flowchart catalog to four stored cardinal ports, and preserve directed edge storage |
| P02 Cardinal Anchor Geometry | `codex/flowchart-cardinal-ports/p02-cardinal-anchor-geometry` | Replace row-band anchor math with exact top/right/bottom/left silhouette anchors and render four consistent handles |
| P03 Canvas Neutral Interaction | `codex/flowchart-cardinal-ports/p03-canvas-neutral-interaction` | Make click/drag flowchart authoring honor gesture order and side-based live preview for neutral ports |
| P04 Flowchart Drop Connect Insert | `codex/flowchart-cardinal-ports/p04-flowchart-drop-connect-insert` | Update quick insert, dropped-node auto-connect, and edge insertion flows for neutral flowchart ports |
| P05 Regression Docs Traceability | `codex/flowchart-cardinal-ports/p05-regression-docs-traceability` | Refresh docs, fixture/checklist evidence, and final regression/traceability for the new flowchart contract |

## Locked Defaults

- Passive flowchart built-ins expose exactly four stored ports with keys `top`, `right`, `bottom`, and `left`.
- Those four ports use `direction="neutral"`, `kind="flow"`, `data_type="flow"`, and `allow_multiple_connections=True`.
- Flowchart port payloads expose a cardinal `side` field that stays aligned with the stored key (`top/right/bottom/left`).
- QML interaction payloads that begin from a neutral flowchart port carry `origin_side`; preview, quick insert, and auto-connect logic must branch on side data rather than fixed `in` / `out` semantics.
- Legacy flowchart port keys (`flow_in`, `flow_out`, `branch_a`, `branch_b`) are removed. There is no migration or alias compatibility layer for existing saved flowchart graphs.
- Decision-branch meaning is no longer encoded in port keys after the migration; edge labels and styling own that meaning.
- When both endpoints are neutral flowchart ports, gesture order is authoritative: the first selected or dragged port is the edge source, and the second is the edge target.
- Auto-selected ports for quick insert, dropped-node auto-connect, and edge insertion use the nearest-facing exposed cardinal port by scene geometry, with distinct sides preferred when an inserted node must serve both inbound and outbound flow edges.
- Non-flowchart nodes keep the current fixed `in` / `out` validation, library filtering, and authoring behavior.
- Flowchart host and drop-preview surfaces continue hiding raw port labels.
- Flowchart anchors are exact silhouette perimeter points for `top`, `right`, `bottom`, and `left`; they must not reuse row-band approximations.
- This packet set is intentionally sequential. Every implementation wave contains exactly one packet.

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

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `FLOWCHART_CARDINAL_PORTS_Pxx_<name>.md`
- Implementation prompt: `FLOWCHART_CARDINAL_PORTS_Pxx_<name>_PROMPT.md`
- Packet wrap-up artifact for each implementation packet: `docs/specs/work_packets/flowchart_cardinal_ports/Pxx_<slug>_WRAPUP.md`
- Status ledger update in [FLOWCHART_CARDINAL_PORTS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement FLOWCHART_CARDINAL_PORTS_PXX_<name>.md exactly. Before editing, read FLOWCHART_CARDINAL_PORTS_MANIFEST.md, FLOWCHART_CARDINAL_PORTS_STATUS.md, and FLOWCHART_CARDINAL_PORTS_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and public graph/node/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update FLOWCHART_CARDINAL_PORTS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P05` may change source/test/docs/fixture files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Keep the persisted edge shape (`source_node_id`, `source_port_key`, `target_node_id`, `target_port_key`) stable even while the flowchart port contract changes.
- Keep non-flowchart node authoring and validation behavior stable unless a packet explicitly changes a shared helper needed for the flowchart neutral-port exception.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
