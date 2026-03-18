# P04 Scene Mutation Contracts Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/arch-third-pass/p04-scene-mutation-contracts`
- Commit Owner: `worker`
- Commit SHA: `dd7d89fe610ce41d28ac19910b08f3348790fa57`
- Changed Files: `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- Artifacts Produced: `docs/specs/work_packets/arch_third_pass/P04_scene_mutation_contracts_WRAPUP.md`
- Added a scene-owned `_GraphSceneContext` so rebuild, history capture/recording, node lookup, and signal emission flow through an explicit boundary instead of bridge-to-service reach-through.
- Rewired `GraphSceneScopeSelection` and `GraphSceneMutationHistory` to depend on that scene context plus focused selection helpers, while keeping the public `GraphSceneBridge` slot/property surface stable for existing QML and test consumers.
- Preserved graph-track, passive-runtime wiring, and shell integration behavior under the existing regression suite without expanding the packet scope beyond the validator-compatible scene files.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_passive_runtime_wiring tests.test_graph_scene_bridge_bind_regression tests.test_main_window_shell -v`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b -v`
- PASS: `./venv/Scripts/python.exe "$(wslpath -w /mnt/c/Users/emre_/.codex/skills/subagent-work-packet-executor/scripts/validate_packet_result.py)" --repo-root "$(wslpath -w /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor)" --packet-spec "$(wslpath -w /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P04_scene_mutation_contracts.md)" --wrapup "$(wslpath -w /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/P04_scene_mutation_contracts_WRAPUP.md)" --changed-file ea_node_editor/ui_qml/graph_scene_bridge.py --changed-file ea_node_editor/ui_qml/graph_scene_mutation_history.py --changed-file ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app on this branch with any workspace that has a few nodes and at least one subnode shell.
- Action: add a node, edit one property from the inspector, then undo and redo once. Expected result: the edited node stays selected, the canvas payload refreshes immediately, and undo/redo restores the mutation cleanly.
- Action: select multiple root-scope nodes, group them into a subnode, then ungroup that shell. Expected result: grouping only succeeds for same-scope selections, the resulting shell/pins appear correctly, and ungroup restores the original nodes and wiring.
- Action: enter a subnode scope, create or connect nodes there, then navigate back to the parent scope. Expected result: mutations stay limited to the active scope and the breadcrumb, selection, and history state remain coherent after navigation.

## Residual Risks

- `_GraphSceneContext` centralizes the internal scene boundary but still writes the final payload arrays and signals through `GraphSceneBridge`; later packets should preserve that seam rather than reintroduce direct service-to-bridge reach-through.
- The packet intentionally leaves passive-media bridge cleanup for `P05`, so those surfaces still depend on the existing stable `GraphSceneBridge` API even though the internal mutation/selection/history coordination is now narrower.

## Ready for Integration

- Yes: the scene mutation boundary is explicit, the public `GraphSceneBridge` contract stayed stable, and both the packet verification suite and review gate passed.
