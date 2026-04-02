# ARCHITECTURE_FOLLOWUP_REFACTOR P06: Graph Authoring Boundary Collapse

## Objective

- Establish one packet-owned graph authoring command boundary so graph mutation, history capture, scene notification, and boundary collaborator use no longer compete across `graph`, `ui.shell`, and `ui_qml`.

## Preconditions

- `P05` is marked `PASS` in [ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md](./ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_FOLLOWUP_REFACTOR` packet is in progress.

## Execution Dependencies

- `P05`

## Target Subsystems

- `ea_node_editor/graph/boundary_adapters.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/transform_fragment_ops.py`
- `ea_node_editor/graph/transform_grouping_ops.py`
- `ea_node_editor/graph/transform_layout_ops.py`
- `ea_node_editor/graph/transform_subnode_ops.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope

- `ea_node_editor/graph/boundary_adapters.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/transform_fragment_ops.py`
- `ea_node_editor/graph/transform_grouping_ops.py`
- `ea_node_editor/graph/transform_layout_ops.py`
- `ea_node_editor/graph/transform_subnode_ops.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/architecture_followup_refactor/P06_graph_authoring_boundary_collapse_WRAPUP.md`

## Required Behavior

- Introduce one packet-owned graph authoring command boundary above the validated mutation helpers.
- Move packet-owned mutation, history-capture, and scene-notification orchestration out of competing `ui_qml` helper stacks.
- Keep `GraphSceneBridge` focused on read-model, selection, scope, and scene-payload projection responsibilities.
- Replace packet-owned mutable global boundary-adapter installation with explicit collaborator injection or ownership local to the authoring path.
- Update inherited graph-scene and graph-surface regression anchors in place when the command boundary or payload path changes.

## Non-Goals

- No viewer-session authority collapse yet; that belongs to `P07`.
- No new graph features or user-facing surface behavior beyond authority cleanup.
- No documentation or QA-matrix closeout yet; that belongs to `P08`.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_followup_refactor/P06_graph_authoring_boundary_collapse_WRAPUP.md`

## Acceptance Criteria

- Packet-owned graph authoring uses one authoritative command boundary.
- Packet-owned graph-scene mutation helpers no longer compete with domain-level mutation ownership.
- Packet-owned global boundary-adapter installation is gone.
- The inherited graph-scene and graph-surface regression anchors pass.

## Handoff Notes

- `P07` builds viewer-session cleanup on top of this narrower scene and authoring boundary.
