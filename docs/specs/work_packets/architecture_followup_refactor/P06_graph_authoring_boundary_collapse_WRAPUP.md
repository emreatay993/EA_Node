# P06 Graph Authoring Boundary Collapse Wrap-up

## Implementation Summary

- Packet: `P06`
- Branch Label: `codex/architecture-followup-refactor/p06-graph-authoring-boundary-collapse`
- Commit Owner: `worker`
- Commit SHA: `3c2ed4cd5d7de2aea7261349a8c48714c39fdb8a`
- Changed Files: `docs/specs/work_packets/architecture_followup_refactor/P06_graph_authoring_boundary_collapse_WRAPUP.md`, `ea_node_editor/graph/boundary_adapters.py`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `tests/test_architecture_boundaries.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_passive_graph_surface_host.py`
- Artifacts Produced: `docs/specs/work_packets/architecture_followup_refactor/P06_graph_authoring_boundary_collapse_WRAPUP.md`, `ea_node_editor/graph/boundary_adapters.py`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `tests/test_architecture_boundaries.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_passive_graph_surface_host.py`

Collapsed packet-owned graph authoring onto one `GraphSceneMutationHistory` command boundary above the validated mutation helpers and moved packet-owned scene notification, history capture, and workspace mutation orchestration out of competing `ui_qml` helper stacks.

Removed packet-owned mutable global boundary-adapter installation. `GraphSceneBridge` now owns concrete boundary adapters for the authoring path and injects them explicitly into the payload builder and mutation service path, while staying focused on read-model, selection, scope, and scene-payload projection responsibilities.

Updated packet-owned regression anchors to assert explicit adapter injection and the narrowed bridge boundary, and fixed the inherited shared-header host anchor to double-click a non-interactive body point instead of the inline-control band.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q` (`14 passed in 3.15s`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_non_scoped_standard_and_passive_titles_use_shared_header_editor_without_pointer_leaks tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_max_performance_degrades_grid_and_minimap_but_preserves_shadows_during_wheel_zoom tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_minimap_keeps_node_geometry_static_when_center_changes --ignore=venv -q` (`3 passed in 2.90s`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py --ignore=venv -q` (`98 passed in 57.81s`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_non_scoped_standard_and_passive_titles_use_shared_header_editor_without_pointer_leaks --ignore=venv -q` (`1 passed in 0.89s`)
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the application from this packet branch and open a workspace with a graph that contains at least one standard node and, if available, one passive standard node or note.

1. Double-click the header title on a standard node, change the title, and press `Enter`. Expected result: single-click still selects the node, double-click opens the shared header editor, `Enter` commits the trimmed title, and the editor closes without opening the node.
2. Reopen the same title editor, change the text, and press `Escape`. Expected result: the edit cancels, no title mutation is emitted, and the editor closes cleanly.
3. Double-click a non-interactive body area on the same node after closing the editor. Expected result: the node opens instead of re-entering title edit, and no stray click or context actions leak from the shared header editor.
4. Perform a packet-owned graph authoring action such as duplicate, delete, fragment edit, move, or layout adjustment, then use undo and redo. Expected result: the scene payload refreshes immediately, mutation history tracks the action once, and the graph state remains consistent after undo/redo.
5. If the graph contains scope-capable nodes, enter and exit scope after a mutation. Expected result: scope selection, scene projection, and authoring operations stay synchronized with no stale payload or selection state.

## Residual Risks

No end-to-end interactive desktop session was executed in this packet; validation is automated plus the manual smoke guidance above.

The passive host suite previously showed an intermittent subprocess crash in `test_graph_canvas_max_performance_degrades_grid_and_minimap_but_preserves_shadows_during_wheel_zoom` with Windows exit code `3221226505` during earlier isolated reruns, but the focused rerun and final exact packet verification both passed. Current evidence points to an inherited environment-sensitive flake rather than a packet-caused regression.

The command-boundary refactor is covered by packet-owned bridge, payload, surface-input, and passive-host regression anchors, but broader app flows outside the packet-owned test surface were not exercised manually here.

## Ready for Integration

- Yes: the packet-owned refactor is committed, the required wrap-up artifact is prepared, the review gate passed, and the exact packet verification command completed cleanly against this branch state.
