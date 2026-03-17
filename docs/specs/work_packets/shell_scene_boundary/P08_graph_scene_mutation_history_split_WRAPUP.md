# P08 Graph Scene Mutation History Split Wrap-Up

## Implementation Summary
- Extracted the mutation, layout, fragment, and history-grouping implementation from `ea_node_editor/ui_qml/graph_scene_bridge.py` into the new helper module `ea_node_editor/ui_qml/graph_scene_mutation_history.py`.
- Kept `GraphSceneBridge` public mutation slot names and call signatures stable by turning the bridge methods into thin delegators over `GraphSceneMutationHistory`.
- Preserved the existing P07 seam by leaving scope/selection ownership in `GraphSceneScopeSelection` and keeping only the minimal bridge-internal hooks (`_node`, `_bounds_for_node_ids`, rebuild/title sync access) that the split still needs.
- Added focused regression coverage in `tests/test_graph_track_b.py` for resize/history behavior, node and edge style mutation payload updates, and fragment paste centering/history behavior.

## Verification
- PASS: `./venv/Scripts/python.exe -m py_compile ea_node_editor/ui_qml/graph_scene_bridge.py ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- PASS: `./venv/Scripts/python.exe -m py_compile tests/test_graph_track_b.py tests/test_graph_surface_input_inline.py tests/test_passive_property_editors.py tests/test_passive_image_nodes.py`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_graph_surface_input_inline tests.test_passive_property_editors tests.test_passive_image_nodes -v`
- Result: `Ran 68 tests in 12.460s`
- Final status: `OK`

## Manual Test Directives
Ready for manual testing.

- Prerequisite: launch the shell on a workspace where you can add standard nodes plus at least one passive/media node.
- Mutation and undo smoke test: add two standard nodes, connect them, move one, resize one, then undo and redo each step. Expected result: node positions, custom size, edge presence, and canvas payloads track each mutation and restore cleanly through undo/redo.
- Group and fragment smoke test: select two connected nodes, group them into a subnode, undo, regroup, then duplicate or paste the selected fragment into a new location. Expected result: grouping remains a single undoable action, duplicated or pasted nodes are reselected, internal wiring is preserved, and external wiring is not copied into the fragment.
- Passive property smoke test: on a passive image panel or passive property-driven node, edit inline or inspector-backed fields such as `source_path`, `caption`, or crop values. Expected result: the edited node updates immediately, the change is applied to the correct `nodeId`, and unrelated nodes do not receive the mutation.

## Residual Risks
- `GraphSceneMutationHistory` still coordinates through `GraphSceneBridge` for rebuilds, title sync, and the P07 scope/selection seam, so later packets should keep moving responsibilities outward rather than re-inlining mutation logic on the bridge.
- This packet verification did not rerun broader shell-level clipboard/history suites such as `tests.main_window_shell.edit_clipboard_history`; wider shell/QML integration coverage remains deferred to later packet work and `P10`.

## Ready for Integration
- Yes. P08 is implemented within the packet write scope, the bridge contract remains stable, and the packet verification slice is green.
