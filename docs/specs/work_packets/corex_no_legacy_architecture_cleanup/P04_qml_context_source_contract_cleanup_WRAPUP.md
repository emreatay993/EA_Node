# P04 QML Context Source Contract Cleanup Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/corex-no-legacy-architecture-cleanup/p04-qml-context-source-contract-cleanup`
- Commit Owner: `worker`
- Commit SHA: `ff191540dd3ddd498ed67eb5e84cf8ce3cef517e`
- Changed Files: `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui/shell/context_bridges.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`, `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`, `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`, `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`, `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `ea_node_editor/ui_qml/shell_inspector_bridge.py`, `ea_node_editor/ui_qml/shell_library_bridge.py`, `ea_node_editor/ui_qml/shell_workspace_bridge.py`, `tests/main_window_shell/bridge_qml_boundaries.py`, `tests/main_window_shell/bridge_support.py`, `tests/main_window_shell/shell_runtime_contracts.py`, `tests/test_main_window_shell.py`, `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P04_qml_context_source_contract_cleanup_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P04_qml_context_source_contract_cleanup_WRAPUP.md`

P04 replaces bridge source fallback discovery with explicit injected sources for shell library, workspace, inspector, graph canvas state, and graph canvas command bridges. The workspace bridge preserves only its explicitly injected shell owner for the existing Add-On Manager presenter; it no longer uses that owner to discover the workspace source.

QML context bootstrapping now exposes a `shellContext` bundle while keeping current top-level services needed by existing QML. Main shell and graph-canvas descendants thread shell services through explicit owner properties instead of raw service-global lookups.

Bridge/QML tests were updated to assert explicit source ownership, the new context bundle, and the absence of graph-canvas descendant raw service lookups.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_support.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Launch the shell from this branch using the project virtual environment and confirm the main workspace opens without QML binding errors.
- Open the Add-On Manager from the shell action. Expected: the panel opens with add-on rows populated, selection details render, and closing the panel restores the workspace view.
- Exercise the graph canvas context menus and node card add-on action. Expected: menus and actions still resolve theme, help, and add-on services through the threaded context without reference errors.
- Use a viewer/content fullscreen path from the graph canvas if a compatible node is available. Expected: fullscreen focus, hinting, and viewer focus clearing behave as before.

## Residual Risks

- No known blockers. The broad QML globals remain where current non-graph-canvas QML still depends on them; P04 narrowed graph-canvas descendants and added the `shellContext` bundle without removing still-live top-level services.

## Ready for Integration

- Yes: P04 is implemented, verified, and committed with a separate wrap-up artifact ready for packet integration.
