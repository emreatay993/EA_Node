# ARCH_SECOND_PASS P02: QML Bridge Contracts

## Objective
- Replace packet-owned reflective bridge forwarding with explicit adapter surfaces and tighten packet-owned QML consumers around the focused bridges instead of raw context-property bypasses.

## Preconditions
- `P00` and `P01` are marked `PASS` in [ARCH_SECOND_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_STATUS.md).
- No later `ARCH_SECOND_PASS` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- packet-owned QML consumers under `ea_node_editor/ui_qml/components/shell/` and `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- shell/QML boundary regression tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/shell/**`
- `tests/test_main_window_shell.py`

## Required Behavior
- Replace packet-owned `getattr`/string-name forwarding and duck-typed host discovery in the focused bridge classes with clearer explicit adapter surfaces where feasible.
- Keep bridge registration names and public QML-facing properties/slots stable unless a packet-owned consumer is explicitly updated in lockstep.
- Repoint packet-owned QML consumers to prefer the focused bridge objects for owned concerns and treat raw context properties as compatibility-only fallbacks.
- Add or tighten regression coverage proving packet-owned shell/QML consumers do not require direct `mainWindow`, `sceneBridge`, or `viewBridge` access for their owned responsibilities.
- Preserve current runtime behavior, object names, and bridge discoverability used by tests.

## Non-Goals
- No deep `GraphCanvas.qml` state extraction yet; `P03` owns that.
- No `GraphNodeHost.qml` or graph-surface control refactor yet.
- No `ShellWindow` host/state refactor beyond the adapter changes required to consume `P01`.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.GraphCanvasBridgeTests tests.test_main_window_shell.ShellLibraryBridgeTests tests.test_main_window_shell.ShellWorkspaceBridgeTests tests.test_main_window_shell.ShellInspectorBridgeTests -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_second_pass/P02_qml_bridge_contracts_WRAPUP.md`

## Acceptance Criteria
- Packet-owned bridge classes no longer depend primarily on reflective `getattr` forwarding for packet-owned properties and calls.
- Packet-owned QML consumers primarily read from focused bridge facades for owned concerns.
- Current shell/QML boundary regression coverage passes.

## Handoff Notes
- `P03` extracts stateful canvas interaction policy after this bridge surface is stabilized.
- Leave compatibility context properties available if packet-owned tests still rely on them, but document any remaining fallback dependencies in the wrap-up.
