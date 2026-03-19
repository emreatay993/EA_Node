# P03 Graph Mutation Validation Boundary Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/arch-fourth-pass/p03-graph-mutation-validation-boundary`
- Commit Owner: `worker`
- Commit SHA: `84c20926994ab2a4c50d5617b71dbb2e3ea28fbe`
- Changed Files: `docs/specs/work_packets/arch_fourth_pass/P03_graph_mutation_validation_boundary_WRAPUP.md`, `ea_node_editor/graph/model.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/graph/rules.py`, `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_graph_track_b.py`, `tests/test_workspace_library_controller_unit.py`
- Artifacts Produced: `docs/specs/work_packets/arch_fourth_pass/P03_graph_mutation_validation_boundary_WRAPUP.md`

Added a registry-aware `ValidatedGraphMutation` boundary under the graph layer, exposed it from `GraphModel`, and moved packet-owned scene authoring writes onto that boundary so node creation, connection authoring, exposed-port changes, and subnode pin-kind changes are validated at write time. Shared port-kind compatibility now comes from the `effective_ports` path instead of duplicated local rule copies, drop-connect capacity checks reuse the canonical helper, and the scene path now prunes invalid subnode shell/pin edges immediately while preserving the previously accepted direct `add_edge` data-port leniency that packet-owned tests still rely on.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_workspace_library_controller_unit tests.test_graph_scene_bridge_bind_regression -v`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b -v`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch with the default built-in registry, open any workspace, and keep the graph canvas visible so you can watch shell ports and edges update live.
- Subnode invalid-edge pruning smoke: create a `Subnode` shell, add one input pin, set that pin kind to `exec`, connect `Start.exec_out` into the shell port, then change the pin kind to `data`. Expected: the outer shell edge disappears immediately after the kind change instead of surviving until save/load or later normalization.
- Shell pin creation smoke: on the same shell, add two input pins and one output pin from the shell UI. Expected: the new shell ports appear immediately, stay exposed without reopening the workspace, and the generated labels follow the existing `Input`, `Input 2`, `Output` pattern.
- Occupied input auto-connect smoke: connect any node into `End.exec_in`, then drag a second `Start` node from the library onto that same input target. Expected: the drop succeeds for the node itself, but the single-capacity input does not auto-connect a second incoming edge.

## Residual Risks

- Raw `GraphModel` mutation methods remain available for packet-external code and tests, so this packet hardens the packet-owned authoring paths without yet forcing every caller in the repository through the validated boundary.
- The authoring boundary intentionally keeps the pre-existing direct `add_edge` behavior that accepts data-port mismatches when the kinds are otherwise valid; tightening that compatibility rule would need a broader behavior decision and downstream coverage.

## Ready for Integration

- Yes: packet-owned graph authoring now routes through a validated mutation boundary, duplicate port-rule logic is reduced to the `effective_ports` path plus canonical capacity helpers, and both the packet verification suite and review gate passed in the project venv.
