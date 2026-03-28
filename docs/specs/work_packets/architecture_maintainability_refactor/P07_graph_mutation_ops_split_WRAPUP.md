# P07 Graph Mutation Ops Split Wrap-up

## Implementation Summary
- Packet: `P07`
- Branch Label: `codex/architecture-maintainability-refactor/p07-graph-mutation-ops-split`
- Commit Owner: `worker`
- Commit SHA: `8208ae1106b961945788b64a9cfa1c61ef34ea18`
- Changed Files: `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/graph/transform_fragment_ops.py`, `ea_node_editor/graph/transform_grouping_ops.py`, `ea_node_editor/graph/transform_layout_ops.py`, `ea_node_editor/graph/transform_subnode_ops.py`, `ea_node_editor/graph/transforms.py`, `tests/test_architecture_boundaries.py`, `tests/test_registry_validation.py`, `docs/specs/work_packets/architecture_maintainability_refactor/P07_graph_mutation_ops_split_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/architecture_maintainability_refactor/P07_graph_mutation_ops_split_WRAPUP.md`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/graph/transform_fragment_ops.py`, `ea_node_editor/graph/transform_grouping_ops.py`, `ea_node_editor/graph/transform_layout_ops.py`, `ea_node_editor/graph/transform_subnode_ops.py`, `ea_node_editor/graph/transforms.py`, `tests/test_architecture_boundaries.py`, `tests/test_registry_validation.py`

`ea_node_editor.graph.transforms` is now a thin public facade. The former bucket has been decomposed into focused packet-owned modules for layout operations, fragment operations, general subnode helpers, and grouping/ungrouping operations, while the existing import surface remains stable for out-of-scope callers.

`WorkspaceMutationService` now imports the focused operation modules directly and keeps packet-owned structural bypass helpers internal as `_..._record` methods. Validated graph writes still flow through `ValidatedGraphMutation` and `GraphInvariantKernel`, so the public mutation authority stays singular while packet-owned multi-step graph ops still have a controlled internal staging path.

The packet-owned regression anchors were updated to match the new seam. Architecture-boundary coverage now proves the service no longer depends on the broad `graph.transforms` bucket and that the public transform surface re-exports focused modules, and registry validation now exercises a grouping/ungrouping round-trip through the mutation service.

## Verification
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py tests/test_workspace_manager.py tests/test_passive_runtime_wiring.py --ignore=venv -q` (`42 passed in 0.19s`)
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_registry_validation.py --ignore=venv -q` (`24 passed in 0.09s`)
- PASS: `git diff --check`
- Final Verification Verdict: PASS

## Manual Test Directives
Ready for manual testing

1. Group and ungroup a small exec chain in the graph canvas.
Prerequisites: launch a native desktop session, open a workspace, add `Start`, `Logger`, and `End` nodes, and connect `Start -> Logger -> End` on the exec ports.
Action: select `Start` and `Logger`, use the graph action that groups the selection into a subnode, inspect the created shell and boundary pin, then ungroup that shell.
Expected result: grouping creates one subnode shell with the selected nodes reparented under it, the external `Logger -> End` connection reroutes through the shell pin, and ungrouping removes the shell/pin and restores the original exec wiring.

2. Copy and paste a grouped fragment that includes subnode-owned structure.
Prerequisites: in the same desktop session, keep a grouped subnode or another nested fragment selected in the graph canvas.
Action: copy the selection, paste it into the same workspace with an offset, and inspect the pasted node parents and any shell-pin edges.
Expected result: pasted nodes receive new ids, nested parent links stay valid, shell edge port keys are remapped to the pasted pin ids, and the pasted fragment appears at the requested offset without corrupting the source selection.

## Residual Risks
- The packet removes public packet-owned raw write helpers from `WorkspaceMutationService`, but private `_..._record` helpers still exist for multi-step internal operations such as fragment insertion and subnode grouping.
- Direct `GraphModel` writes still exist outside this packet scope, so the “single mutation authority” outcome is enforced for packet-owned graph operations rather than every out-of-scope caller in the repository.

## Ready for Integration
- Yes: the transform bucket is split into focused graph modules, packet-owned graph operations now route through one public mutation service surface with one invariant kernel for validated writes, the required verification and review gate passed, and the updated regression anchors cover the new structure.
