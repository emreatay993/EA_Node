# P04 QML Surface Wrap-Up

## Implementation Summary
- Packet: `P04`
- Branch Label: `codex/v1-classic-explorer-folder-node/p04-qml-surface`
- Commit Owner: `worker`
- Commit SHA: `900e3d366590597a8db66ae69f0c8b89e031221f`
- Changed Files: ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml, ea_node_editor/ui_qml/components/graph/passive/GraphClassicExplorerSurface.qml, tests/graph_surface/passive_host_interaction_suite.py, tests/test_graph_surface_input_inline.py, docs/specs/work_packets/v1_classic_explorer_folder_node/P04_qml_surface_WRAPUP.md
- Artifacts Produced: ea_node_editor/ui_qml/components/graph/passive/GraphClassicExplorerSurface.qml, docs/specs/work_packets/v1_classic_explorer_folder_node/P04_qml_surface_WRAPUP.md

Implemented `io.folder_explorer` routing in the graph surface loader and added the V1 Classic Explorer passive QML surface. The surface renders Explorer-style title, command, breadcrumb, search, side navigation, details columns, row selection, context menu actions, drag path-pointer payloads, maximize, and close controls. Filesystem and graph mutations are dispatched through the P03 action router/command bridge; transient navigation, search, sort, selection, context, and maximized state remains QML-local.

Focused regressions now cover loader routing, initial listing consumption, navigation/search/sort/context command payloads, drag payload shape, close routing, and the no-transient-property-commit invariant.

## Verification
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py -k folder_explorer --ignore=venv -q` -> 2 passed, 64 deselected.
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_inline.py -k folder_explorer --ignore=venv -q` -> 2 passed, 10 deselected.
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k folder_explorer --ignore=venv -q` -> 2 passed.
- FAIL: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py tests/test_graph_surface_input_inline.py tests/graph_surface/passive_host_interaction_suite.py -k "folder_explorer or graph_surface" --ignore=venv -q` -> completed in 499.30s with 106 passed and 9 failed. Failures were in existing non-folder graph-canvas/host tests: live resize geometry, wheel-zoom shadow/proxy behavior, title icon reserve, locked placeholder routing, and duplicated direct-suite graph-canvas cases.
- FAIL: Targeted rerun of the failing wrapper subset reduced to 3 persistent non-folder failures: `test_graph_canvas_routes_live_resize_geometry_through_edge_layer_and_scene_commit`, `test_title_icon_renders_for_non_passive_titles_and_uses_centered_reserve`, and `test_locked_placeholder_routes_to_addon_manager_and_blocks_mutations`.
- FAIL: Retry baseline-family command in this P04 worktree, `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py tests/graph_surface/passive_host_interaction_suite.py -k "locked_placeholder_routes or title_icon_renders_for_non_passive_titles or live_resize_geometry" --ignore=venv -q`, -> 5 failed, 98 deselected. The failures are the same 3 unique non-folder cases, with live resize geometry and title icon reserve duplicated through `tests/graph_surface/passive_host_interaction_suite.py`.
- FAIL: Executor baseline comparison on Wave 3 base `99bcc8e34f241c80b9128366be36c646dc1a5a5d` reported the same 3 unique non-folder failure families before P04: live resize geometry, non-passive title icon reserve, and locked placeholder add-on manager routing.
- PASS: Retry review gate, `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py -k folder_explorer --ignore=venv -q`, -> 2 passed, 64 deselected.
- Final Verification Verdict: `FAIL`

## Manual Test Directives
Too soon for manual testing.

P04 is user-visible once an `io.folder_explorer` node can be created or selected in the shell, but P05 still owns shell/library/inspector exposure. Manual testing becomes worthwhile after P05 exposes the node in the normal UI path.

Next manual-test condition: after P05, launch with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`, add a Folder Explorer node, set a real folder path, verify breadcrumbs/details/context actions route through confirmations, and confirm drag-out creates an `io.path_pointer`.

## Residual Risks
- The exact full packet verification command currently fails in non-folder graph-canvas/host tests that are outside the P04 write scope. Executor baseline comparison confirms the persistent 3 unique failure families already fail on Wave 3 base before P04.
- No P04-scope code/test change can make the required full command pass honestly without changing unrelated non-folder behavior or hiding baseline failures. The folder-explorer review gate and folder-explorer packet slices pass.
- End-user creation and inspector/library exposure remain owned by P05, so manual UI testing is premature from the normal shell workflow.
- Rename and New Folder menu commands rely on the existing P03 confirmation/mutation bridge; this packet does not add inline rename prompts or filesystem service behavior.

## Ready for Integration
- No: folder-explorer P04 behavior is implemented and packet-owned tests pass, but the required full verification command is blocked by baseline non-folder failures that need upstream resolution or executor waiver before integration is marked pass.
