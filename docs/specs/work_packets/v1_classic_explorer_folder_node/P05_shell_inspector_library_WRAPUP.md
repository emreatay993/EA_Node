# P05 Shell Inspector Library Wrap-Up

## Implementation Summary
- Packet: `P05`
- Branch Label: `codex/v1-classic-explorer-folder-node/p05-shell-inspector-library`
- Commit Owner: `worker`
- Commit SHA: `d4f1d5a5eeb54abf9a87e0babd86ff6a91004b4d`
- Changed Files: ea_node_editor/ui/shell/window_library_inspector.py, ea_node_editor/ui_qml/components/shell/InspectorPropertyEditor.qml, ea_node_editor/ui_qml/shell_inspector_bridge.py, tests/main_window_shell/passive_property_editors.py, tests/test_graph_surface_input_inline.py, tests/test_serializer.py, tests/test_window_library_inspector.py, docs/specs/work_packets/v1_classic_explorer_folder_node/P05_shell_inspector_library_WRAPUP.md
- Artifacts Produced: docs/specs/work_packets/v1_classic_explorer_folder_node/P05_shell_inspector_library_WRAPUP.md

Implemented P05 shell/library/inspector exposure for `io.folder_explorer`. The node is now covered as discoverable in the existing `Input / Output` library grouping, `current_path` is projected as a path editor with folder dialog mode, and the shell inspector bridge uses the existing folder picker for folder-path properties while leaving property commits on the existing graph mutation path.

Added focused coverage for inspector folder browsing, Classic Explorer surface current-path mutation routing, and `.sfe` persistence output proving only `current_path` is serialized for the node while transient Explorer UI state remains absent.

## Verification
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_window_library_inspector.py tests/main_window_shell/passive_property_editors.py tests/test_graph_surface_input_inline.py tests/test_serializer.py --ignore=venv -q` completed with `66 passed, 4 warnings`.
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/passive_property_editors.py -k folder --ignore=venv -q` completed with `2 passed, 8 warnings`.
- PASS: Warnings were dependency deprecation warnings from `ansys.dpf.core` operator rename notices only.
- Final Verification Verdict: `PASS`

## Manual Test Directives
Ready for manual testing
- Prerequisite: Launch the app from this branch with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`.
- Library discovery: Open the node library, expand `Input / Output`, or search for `folder explorer`; expect `Folder Explorer` to appear and be addable to the graph.
- Inspector folder browse: Select a `Folder Explorer` node, use the `Current Path` Browse button in the inspector, and choose a directory; expect the selected directory to appear in the inspector and persist on the node as `current_path`.
- Surface path change: On the Classic Explorer node surface, change the path through the surface path editor; expect navigation to update the node `current_path` through the normal graph property update route.
- Persistence smoke: Save and reopen the project; expect the node to restore `current_path` only, with search text, navigation history, selection, sort state, context menu state, and maximized state reset as transient UI state.

## Residual Risks
- No known P05 packet-local residual risks.
- The verification run still emits existing `ansys.dpf.core` deprecation warnings unrelated to this packet.

## Ready for Integration
- Yes: P05 is implemented, verified, and committed on the assigned packet branch with no known packet-local blockers.
