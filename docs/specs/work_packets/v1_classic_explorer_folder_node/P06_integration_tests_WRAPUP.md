# P06 Integration Tests Wrap-Up

## Implementation Summary
- Packet: `P06`
- Branch Label: `codex/v1-classic-explorer-folder-node/p06-integration-tests`
- Commit Owner: `worker`
- Commit SHA: `5a9927d54e33ca9b740c3d80e330364f7f716f10`
- Changed Files: tests/main_window_shell/passive_property_editors.py, tests/test_folder_explorer_filesystem_service.py, tests/test_graph_action_contracts.py, tests/test_graph_surface_input_inline.py, tests/test_integrations_track_f.py, tests/test_serializer.py, docs/specs/work_packets/v1_classic_explorer_folder_node/P06_integration_tests_WRAPUP.md
- Artifacts Produced: docs/specs/work_packets/v1_classic_explorer_folder_node/P06_integration_tests_WRAPUP.md

Added P06 integration regressions over the completed Classic Explorer folder node path. The tests now cover graph-created `io.folder_explorer` nodes driving real temp-directory listings, breadcrumb targets, QML breadcrumb/context/drag command emission, QML command aliases for drag-to-Path-Pointer and new-window creation, confirmed rename/cut/paste mutation behavior, inspector folder browsing persisted as `current_path`, and transient surface state being discarded before project reserialization.

No product source code was changed.

## Verification
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_folder_explorer_filesystem_service.py -k folder_explorer --ignore=venv -q` completed with `21 passed, 1 warning`.
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_integrations_track_f.py tests/test_graph_surface_input_inline.py tests/test_serializer.py tests/main_window_shell/passive_property_editors.py -k folder_explorer --ignore=venv -q` completed with `12 passed, 78 deselected, 4 warnings`.
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_integrations_track_f.py tests/test_folder_explorer_filesystem_service.py tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py tests/test_window_library_inspector.py tests/main_window_shell/passive_property_editors.py tests/test_serializer.py --ignore=venv -q` completed with `225 passed, 4 warnings, 18 subtests passed`.
- PASS: `.\venv\Scripts\python.exe scripts\run_verification.py --mode fast --dry-run` completed and assembled the fast context-budget and pytest commands.
- PASS: Warnings were existing viewer-host SyntaxWarning or dependency deprecation warnings from `ansys.dpf.core` operator rename notices; the review-gate run also emitted a non-fatal pytest temp cleanup permission message after the successful exit.
- Final Verification Verdict: PASS

## Manual Test Directives
Ready for manual testing
- Prerequisite: Launch the app from this branch with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`.
- Create and browse: Add a `Folder Explorer` node from `Input / Output`, set `Current Path` to a temporary folder containing at least one file and one child folder, and expect the Classic Explorer surface to list those entries with breadcrumb navigation available.
- Commands and Path Pointer: From a listed row, use the context menu or drag-out flow to send the item to COREX as a Path Pointer; expect an `io.path_pointer` node with the selected path and the correct file/folder mode.
- Confirmed mutation smoke: In a disposable temp folder, use Classic Explorer row actions for rename/delete or cut/paste and confirm the prompt; expect only the selected temp path to change, with sibling files untouched. Cancel the prompt once and expect no filesystem change.
- Persistence smoke: Save and reopen the project after browsing and changing search/sort/selection state; expect only `current_path` to restore on the node, while search, sort, selection, context menu state, maximized state, and navigation history reset as transient state.

## Residual Risks
- No known P06 packet-local residual risks.
- Verification still reports existing environment/dependency warnings unrelated to this packet.

## Ready for Integration
Yes: P06 is implemented, verified, and committed on the assigned packet branch with no known packet-local blockers.
