# ARCH_FIFTH_PASS P04: Bridge Contract Foundation

## Objective
- Introduce focused canvas state/command bridge contracts and register them in the shell context while keeping existing compatibility exports alive for one packet so later QML migration can be behavior-preserving.

## Preconditions
- `P03` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- QML context bootstrap and bridge registration
- canvas state vs command bridge boundaries
- bridge-focused shell regression tests

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/test_graph_surface_input_contract.py`
- `docs/specs/work_packets/arch_fifth_pass/P04_bridge_contract_foundation_WRAPUP.md`

## Required Behavior
- Add a read-heavy `graphCanvasStateBridge` that owns graphics preferences, scene payloads, selection, and viewport state exposure.
- Add a command-focused `graphCanvasCommandBridge` that owns shell/canvas command invocations previously routed through broad fallback surfaces.
- Keep the existing `graphCanvasBridge` export as a compatibility adapter in this packet so no QML behavior changes are required yet.
- Keep `mainWindow`, `sceneBridge`, and `viewBridge` compatibility exports alive in this packet.
- Add or update bridge regression coverage so the new bridges are validated before the QML migration packet starts.

## Non-Goals
- No QML call-site migration yet; `P05` owns that.
- No removal of raw compatibility globals in this packet.
- No shell-controller or mutation-boundary work beyond what bridge registration strictly requires.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_surface_input_contract.py -q -k "ShellLibraryBridgeTests or ShellInspectorBridgeTests or ShellWorkspaceBridgeTests or GraphCanvasBridgeTests"`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py -q -k "GraphCanvasBridgeTests"`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P04_bridge_contract_foundation_WRAPUP.md`

## Acceptance Criteria
- Focused canvas state and command bridge types exist and are exported through the QML context.
- Existing compatibility bridge/global exports remain available so user-facing behavior is unchanged after this packet.
- Bridge-focused packet verification passes under offscreen Qt.

## Handoff Notes
- `P05` removes the raw QML fallbacks and migrates QML to the new bridge names. Keep this packet additive and compatibility-preserving.
- Do not broaden the new bridges beyond canvas state and canvas command responsibilities.
