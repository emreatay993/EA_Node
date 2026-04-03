# ARCHITECTURE_RESIDUAL_REFACTOR P03: Graph Scene Bridge Decomposition

## Objective

- Split broad graph-scene projection, command, history, and policy responsibilities into narrower packet-owned seams without reintroducing raw shell or QML globals.

## Preconditions

- `P02` is marked `PASS` in [ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md](./ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_RESIDUAL_REFACTOR` packet is in progress.

## Execution Dependencies

- `P02`

## Target Subsystems

- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/architecture_residual_refactor/P03_graph_scene_bridge_decomposition_WRAPUP.md`

## Required Behavior

- Split packet-owned graph-scene responsibilities into narrower read-model versus command, history, or policy seams where the current bridge is too broad.
- Keep `GraphCanvas.qml` integration-contract methods stable for shell-owned workflows.
- Do not re-expand QML context ownership or introduce raw host globals to compensate for the decomposition.
- Update inherited graph-scene regression anchors in place instead of adding duplicate later-wave tests for the same seam.

## Non-Goals

- No viewer-session authority split yet; that belongs to `P04`.
- No runtime-snapshot decoupling or graph-domain service work yet.
- No new graph-authoring features.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_residual_refactor/P03_graph_scene_bridge_decomposition_WRAPUP.md`

## Acceptance Criteria

- Packet-owned graph-scene consumers bind to narrower read or command seams instead of one omnibus bridge surface.
- `GraphCanvas.qml` integration-contract methods remain stable.
- The inherited graph-scene and input-routing regression anchors pass.

## Handoff Notes

- `P04` narrows the viewer stack against this smaller graph-scene surface.
