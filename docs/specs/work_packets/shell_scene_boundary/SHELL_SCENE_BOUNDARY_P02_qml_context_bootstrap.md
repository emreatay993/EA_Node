# SHELL_SCENE_BOUNDARY P02: QML Context Bootstrap

## Objective
- Extract QML engine/context registration from `ShellWindow._build_qml_shell()` and introduce dedicated facade skeletons so later packets can migrate QML consumers off raw app bridges without reopening QML bootstrap wiring.

## Preconditions
- `P00` is marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py` (new)
- `ea_node_editor/ui_qml/shell_library_bridge.py` (new skeleton)
- `ea_node_editor/ui_qml/shell_workspace_bridge.py` (new skeleton)
- `ea_node_editor/ui_qml/shell_inspector_bridge.py` (new skeleton)
- `ea_node_editor/ui_qml/graph_canvas_bridge.py` (new skeleton)
- `tests/test_main_window_shell.py`
- `tests/test_graph_scene_bridge_bind_regression.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `tests/test_main_window_shell.py`
- `tests/test_graph_scene_bridge_bind_regression.py`

## Required Behavior
- Extract QML `QQuickWidget` engine setup, image-provider registration, and context-property registration into a dedicated bootstrap/helper module.
- Instantiate and register narrow facade objects for the later shell-library, shell-workspace, shell-inspector, and graph-canvas packets.
- Keep current context-property names available so the app still boots before the consumer-migration packets land.
- Keep `ShellWindow` startup behavior, `MainShell.qml` loading, and render-frame hookup behavior stable.
- Avoid assigning real consumer logic to the new bridge skeletons beyond what is needed to bootstrap them safely for later packets.

## Non-Goals
- No consumer migration in `MainShell.qml` or shell component QML files yet.
- No `GraphCanvas.qml` dependency rewrite yet.
- No `GraphSceneBridge` internal extraction yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_graph_scene_bridge_bind_regression -v`

## Acceptance Criteria
- `ShellWindow._build_qml_shell()` no longer owns all context-registration detail inline.
- The new facade objects are bootstrapped and available for later packets.
- Existing shell load/regression tests still pass with the legacy context properties left intact.

## Handoff Notes
- `P03` through `P05` assume the facade skeletons from this packet already exist and are bound into the QML context.
