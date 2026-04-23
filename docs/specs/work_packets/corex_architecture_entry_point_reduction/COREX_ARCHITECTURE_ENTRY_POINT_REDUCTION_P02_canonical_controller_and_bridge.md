# COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION P02: Canonical Controller and Bridge

## Packet Metadata

- Packet: `P02`
- Title: `Canonical Controller and Bridge`
- Execution Dependencies: `P01`
- Worker model: `gpt-5.5`
- Worker reasoning effort: `xhigh`

## Objective

- Add the canonical internal owner for high-level graph UI actions and expose it to QML through a narrow bridge while old PyQt and QML routes remain functional.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only source files needed for controller/bridge wiring and inherited action-contract tests

## Preconditions

- `P01` is `PASS`.
- `ea_node_editor/ui/shell/graph_action_contracts.py` exists and is covered by `tests/test_graph_action_contracts.py`.

## Execution Dependencies

- `P01`

## Target Subsystems

- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui_qml/graph_action_bridge.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`

## Conservative Write Scope

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P02_canonical_controller_and_bridge_WRAPUP.md`
- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui_qml/graph_action_bridge.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`

## Required Behavior

- Add `GraphActionController` with `trigger(action_id: str, payload: Mapping[str, object] | None = None) -> bool`.
- The controller must own only high-level graph UI actions. It delegates to existing behavior owners such as shell presenters, `workspace_library_controller`, `graph_canvas_presenter`, `graph_canvas_host_presenter`, scene command bridges, and existing private helpers without duplicating their behavior.
- Add payload normalization inside the controller or contract layer so missing or invalid required payload keys return `False` rather than raising from QML.
- Add `GraphActionBridge(QObject)` with at least:
  - `trigger_graph_action(action_id: str, payload: QVariantMap) -> bool`
  - a read-only way for QML/tests to query available action ids or action-state metadata when useful for contract tests
- Wire `GraphActionController` and `GraphActionBridge` into shell composition and QML context as `graphActionBridge`.
- Do not remove or rewire existing PyQt actions, shell wrappers, or `GraphCanvasCommandBridge` high-level slots in this packet. The old routes must remain the runtime callers until `P03` and `P04`.
- Update shell/QML bridge bootstrap tests so `graphActionBridge` is expected and typed.
- Update inherited action contract tests when bridge-level payload rules refine the `P01` inventory.

## Non-Goals

- Do not route `QAction.triggered` connections through the new controller; `P03` owns that.
- Do not route QML context menus or node delegates through `graphActionBridge`; `P04` owns that.
- Do not remove `GraphCanvasCommandBridge` high-level slots.
- Do not change saved project data or graph mutation behavior.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py -k "ContextBootstrap or GraphCanvasBridge" --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P02_canonical_controller_and_bridge_WRAPUP.md`
- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui_qml/graph_action_bridge.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`

## Acceptance Criteria

- `graphActionBridge` is registered in the QML context and covered by shell bootstrap tests.
- `GraphActionController.trigger()` delegates at least one representative action from each covered family without changing the old call sites.
- Invalid or incomplete payloads return `False` consistently.
- `P01` action-contract tests still pass.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- `P03` will connect PyQt menu actions and shortcuts to `GraphActionController`.
- `P04` will connect QML context menus and node delegate high-level actions to `graphActionBridge` and may remove obsolete `GraphCanvasCommandBridge` high-level slots.
