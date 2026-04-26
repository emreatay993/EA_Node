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
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_inline.py -k folder_explorer --ignore=venv -q` -> 2 passed, 10 deselected.
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k folder_explorer --ignore=venv -q` -> 2 passed.
- PASS: Baseline graph-surface blocker fix landed on updated Wave 3 base `b7788553d03ee6ae4f2fbb7872bf5022443a4afa`.
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py tests/test_graph_surface_input_inline.py tests/graph_surface/passive_host_interaction_suite.py -k "folder_explorer or graph_surface" --ignore=venv -q` -> 115 passed in 240.93s.
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py -k folder_explorer --ignore=venv -q` -> 2 passed, 64 deselected.
- Final Verification Verdict: `PASS`

## Manual Test Directives
Too soon for manual testing.

P04 is user-visible once an `io.folder_explorer` node can be created or selected in the shell, but P05 still owns shell/library/inspector exposure. Manual testing becomes worthwhile after P05 exposes the node in the normal UI path.

Next manual-test condition: after P05, launch with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`, add a Folder Explorer node, set a real folder path, verify breadcrumbs/details/context actions route through confirmations, and confirm drag-out creates an `io.path_pointer`.

## Residual Risks
- No known P04 packet-local residual risks after the updated Wave 3 base resolved the baseline graph-surface blockers.
- End-user creation and inspector/library exposure remain owned by P05, so manual UI testing is premature from the normal shell workflow.
- Rename and New Folder menu commands rely on the existing P03 confirmation/mutation bridge; this packet does not add inline rename prompts or filesystem service behavior.

## Ready for Integration
- Yes: P04 folder-explorer surface behavior is implemented and the required packet verification command passes on the updated Wave 3 base.
