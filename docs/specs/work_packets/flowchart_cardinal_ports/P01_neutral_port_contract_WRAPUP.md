# P01 Neutral Port Contract Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/flowchart-cardinal-ports/p01-neutral-port-contract`
- Commit Owner: `worker`
- Commit SHA: `cefebfe9a566b0ca58095b40f75c20c615997e03`
- Changed Files: `ea_node_editor/nodes/types.py`, `ea_node_editor/nodes/registry.py`, `ea_node_editor/nodes/builtins/passive_flowchart.py`, `ea_node_editor/graph/effective_ports.py`, `ea_node_editor/graph/rules.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/graph/transforms.py`, `ea_node_editor/ui/graph_interactions.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `tests/test_passive_flowchart_catalog.py`, `tests/test_passive_node_contracts.py`, `tests/test_registry_validation.py`, `tests/graph_track_b/scene_and_model.py`, `docs/specs/work_packets/flowchart_cardinal_ports/P01_neutral_port_contract_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/flowchart_cardinal_ports/P01_neutral_port_contract_WRAPUP.md`

Extended the port contract with `direction="neutral"` plus cardinal `side` metadata, while keeping existing `in` and `out` validation intact for non-flowchart nodes. The passive flowchart catalog now stores four neutral flow ports keyed `top`, `right`, `bottom`, and `left` on all nine built-in node types, with no legacy `flow_in` / `flow_out` / `branch_a` / `branch_b` aliases.

Graph-core connect handling still persists directed edges, but it now accepts neutral flowchart ports as explicit source/target endpoints and keeps deterministic non-gesture authoring through `preferred_connection_port()`, `port_supports_outgoing_edge()`, `port_supports_incoming_edge()`, `port_side()`, and `port_layout_direction()`. `connect_nodes()` now preserves the existing left-to-right heuristic with a top-to-bottom tie-break, then picks facing cardinal ports based on dominant scene axis so later packets can reuse the same helper names and orientation rule.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest tests/test_passive_flowchart_catalog.py tests/test_passive_node_contracts.py tests/test_registry_validation.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -k "flowchart or connect_nodes" -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_passive_flowchart_catalog.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: stay on `codex/flowchart-cardinal-ports/p01-neutral-port-contract` and launch the app with the worktree venv so the passive flowchart catalog comes from this branch.
- Action: add any built-in passive flowchart node type, such as `Start`, `Decision`, or `End`, to a scene and inspect its handles.
- Expected result: each built-in flowchart node shows four stored handles keyed `top`, `right`, `bottom`, and `left`, with no `flow_in`, `flow_out`, `branch_a`, or `branch_b` labels exposed in the authored contract.
- Action: place two passive flowchart `Process` nodes left-to-right and use the existing connect-nodes action.
- Expected result: the created edge is stored from the left node's `right` port to the right node's `left` port.
- Action: place two passive flowchart `Process` nodes vertically and use the existing connect-nodes action.
- Expected result: the created edge is stored from the upper node's `bottom` port to the lower node's `top` port.

## Residual Risks

- Live GraphCanvas gesture payloads and `origin_side` propagation are still owned by later packets; this packet only establishes the neutral contract and the deterministic graph-core helper behavior they should reuse.
- Flowchart handle placement still uses the pre-existing row-band approximation bridge through `port_layout_direction()` until P02 replaces it with exact top/right/bottom/left silhouette anchors.

## Ready for Integration

- Yes: the neutral flowchart port contract is implemented within the packet write scope, the required verification and review-gate commands pass with `./venv/Scripts/python.exe`, and the wrap-up artifact records the substantive packet commit SHA.
