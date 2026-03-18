# P06 Graph Scene Core Contracts Wrap-Up

## Implementation Summary

- Packet: `P06`
- Branch Label: `codex/arch-second-pass/recovery-p06-20260318`
- Commit Owner: `worker`
- Commit SHA: `babd13135312739916eaf82e59fb30667f66e50e`
- Changed Files: `ea_node_editor/execution/compiler.py`, `ea_node_editor/graph/effective_ports.py`, `ea_node_editor/graph/transforms.py`, `ea_node_editor/nodes/builtins/subnode.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `ea_node_editor/ui_qml/graph_scene_scope_selection.py`, `tests/test_graph_track_b.py`, `tests/test_main_window_shell.py`, `tests/test_passive_runtime_wiring.py`
- Artifacts Produced: `docs/specs/work_packets/arch_second_pass/P06_graph_scene_core_contracts_WRAPUP.md`

- Centralized packet-owned subnode semantics in `nodes/builtins/subnode.py` and rewired graph/execution helpers to use shared type and pin-definition contracts instead of duplicating special-case checks.
- Moved packet-owned layout and fragment helpers out of `GraphSceneMutationHistory` into `graph/transforms.py`, leaving the mutation layer focused on history-orchestrated scene actions while `GraphSceneBridge` and `GraphScenePayloadBuilder` now exchange explicit inputs/results instead of leaning on bridge-private state.
- Added regression coverage for shell-pin planning, registry-free subnode compilation, and recovery-worktree-safe shell test loading while preserving existing graph authoring and passive/runtime behavior.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe -m unittest tests.test_graph_track_b -v`
- PASS: `QT_QPA_PLATFORM=offscreen /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_passive_runtime_wiring tests.test_main_window_shell -v`
- PASS: `python3 /mnt/c/Users/emre_/.codex/skills/subagent-work-packet-executor/scripts/validate_packet_result.py --repo-root /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor_wave5_recovery_cOV88y/p06_worktree --packet-spec /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_P06_graph_scene_core_contracts.md --wrapup /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor_wave5_recovery_cOV88y/p06_worktree/docs/specs/work_packets/arch_second_pass/P06_graph_scene_core_contracts_WRAPUP.md --changed-file ea_node_editor/execution/compiler.py --changed-file ea_node_editor/graph/effective_ports.py --changed-file ea_node_editor/graph/transforms.py --changed-file ea_node_editor/nodes/builtins/subnode.py --changed-file ea_node_editor/ui_qml/graph_scene_bridge.py --changed-file ea_node_editor/ui_qml/graph_scene_mutation_history.py --changed-file ea_node_editor/ui_qml/graph_scene_payload_builder.py --changed-file ea_node_editor/ui_qml/graph_scene_scope_selection.py --changed-file tests/test_graph_track_b.py --changed-file tests/test_main_window_shell.py --changed-file tests/test_passive_runtime_wiring.py`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: start the shell with a workspace where you can add `core.subnode`, `core.subnode_input`, and `core.subnode_output` nodes.
- Add two input pins and one output pin to a subnode shell, then open that shell scope. Expected: labels increment as `Input`, `Input 2`, and `Output`; the shell exposes the new ports immediately; entering the subnode scope still works.
- Group a small in-scope selection into a subnode, duplicate or paste that fragment near a new location, then ungroup it. Expected: the grouped history stays single-step, pasted content lands around the requested center, and ungroup restores the inner nodes and wiring.
- Compile or run a workspace that mixes passive nodes with subnode authoring nodes. Expected: passive and compile-only authoring nodes stay excluded from runtime execution while regular runtime nodes keep the same effective wiring.

## Residual Risks

- `GraphSceneMutationHistory` still owns bridge-bound history capture and model mutation orchestration; removing more of that reach-through would require a wider scene-command seam than this conservative packet allowed.
- `tests/test_main_window_shell.py` now skips split shell test modules that are absent from this isolated recovery worktree, so shell verification here covers the modules present on disk rather than assuming the full split-test set is available.

## Ready for Integration

- Yes: `P06` centralizes packet-owned graph/subnode contracts, keeps the public scene bridge behavior stable, and passes the packet review gate plus full verification in the recovery worktree.
