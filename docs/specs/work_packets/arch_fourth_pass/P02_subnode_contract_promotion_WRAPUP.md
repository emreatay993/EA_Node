# P02 Subnode Contract Promotion Wrap-Up

## Implementation Summary

- Packet: `P02`
- Branch Label: `codex/arch-fourth-pass/p02-subnode-contract-promotion`
- Commit Owner: `worker`
- Commit SHA: `e348511cdd3a86db12589233f47d8402b313a2ed`
- Changed Files: `docs/specs/work_packets/arch_fourth_pass/P02_subnode_contract_promotion_WRAPUP.md`, `ea_node_editor/execution/compiler.py`, `ea_node_editor/graph/effective_ports.py`, `ea_node_editor/graph/subnode_contract.py`, `ea_node_editor/graph/transforms.py`, `ea_node_editor/nodes/builtins/subnode.py`, `tests/test_registry_validation.py`
- Artifacts Produced: `docs/specs/work_packets/arch_fourth_pass/P02_subnode_contract_promotion_WRAPUP.md`

Promoted subnode constants, pin-definition helpers, and authoring/runtime classification into `ea_node_editor.graph.subnode_contract`, then retargeted the packet-owned graph and execution layers to that lower-level seam. The builtin subnode plugin now consumes the promoted contract while preserving the same public type ids, pin property keys, authored document shape, compiled-runtime flattening behavior, and nested-node diagnostic mapping.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_worker tests.test_graph_track_b tests.test_registry_validation tests.test_passive_runtime_wiring -v`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_worker -v`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch with the default built-in registry and open a workspace where you can author and run a basic subnode flow.
- Authoring smoke: create a `Subnode` shell, add one `Subnode Input` and one `Subnode Output`, then rename the pins and change one pin kind/data type. Expected: the shell ports update immediately with the same labels, directions, and kind/data-type normalization as before the refactor.
- Nested execution smoke: wire `Start -> Subnode -> End`, place a `Logger` inside the subnode between an exec input pin and an exec output pin, then run the workspace. Expected: the run completes, the inner logger executes, and the shell/pin authoring nodes do not appear as runtime-executed nodes.
- Diagnostics smoke: replace the inner logger with a `Python Script` that raises an exception and run again. Expected: the failure reports the inner script node id and traceback rather than attributing the error to the subnode shell or its pin nodes.

## Residual Risks

- Packet-owned graph and execution modules now depend on the promoted contract, but packet-external UI/shell callers still consume builtin subnode re-exports until later packets narrow those boundaries.
- The promoted contract lives under `ea_node_editor.graph` because this packet's write scope did not include a more neutral shared package; a future packet would need broader scope to move it lower than both graph and builtin registration.

## Ready for Integration

- Yes: the subnode contract is promoted for packet-owned graph/execution code, builtin registration keeps the existing public ids and authored shape, and the required verification plus review gate both passed in the project venv.
