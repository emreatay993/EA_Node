# UI_CONTEXT_SCALABILITY_REFACTOR P03: Graph Scene Bridge Packet Split

## Objective

- Move graph-scene state-support code into a focused package and leave `graph_scene_bridge.py` as a thin composition surface so graph scene work stops consuming one broad Python bridge file.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_REFACTOR` packet is in progress.

## Execution Dependencies

- `P02`

## Target Subsystems

- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene/__init__.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/policy_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/read_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene/__init__.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/policy_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/read_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P03_graph_scene_bridge_packet_split_WRAPUP.md`

## Required Behavior

- Create `ea_node_editor/ui_qml/graph_scene/` as the packet-owned support package for graph-scene bridge logic.
- Move read, command, policy, context, cache, and pending-action support out of `graph_scene_bridge.py` into the focused package.
- Keep `graph_scene_bridge.py` as the curated export and composition surface only; end it at or below `300` lines.
- Update inherited graph-scene and graph-surface regression anchors in place when bridge object names, properties, or payload seams change.
- Do not reintroduce packet-owned QML globals or host fallbacks while splitting the bridge.

## Non-Goals

- No `GraphCanvas.qml` root packetization yet; that belongs to `P04`.
- No edge-rendering packetization yet.
- No viewer-specific cleanup yet.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py tests/test_main_window_shell.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_refactor/P03_graph_scene_bridge_packet_split_WRAPUP.md`
- `ea_node_editor/ui_qml/graph_scene/__init__.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/policy_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/read_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`

## Acceptance Criteria

- Packet-owned graph-scene support logic no longer lives directly in `graph_scene_bridge.py`.
- `graph_scene_bridge.py` stays at or below `300` lines.
- The inherited graph-scene and graph-surface regression anchors pass.

## Handoff Notes

- `P04` reduces the graph-canvas root on top of the narrower graph-scene bridge surface from this packet.
