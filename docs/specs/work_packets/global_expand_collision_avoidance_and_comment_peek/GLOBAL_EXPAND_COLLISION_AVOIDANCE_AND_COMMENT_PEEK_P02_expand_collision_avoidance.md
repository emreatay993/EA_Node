# GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK P02: Expand Collision Avoidance

## Packet Metadata

- Packet: `P02`
- Title: `Expand Collision Avoidance`
- Owning Source Subsystem Packet: [Graph Scene Packet](../ui_context_scalability_refactor/GRAPH_SCENE_PACKET.md)
- Owning Regression Packet: [Graph Surface Test Packet](../ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md)
- Inherited Secondary Subsystem Docs: [Graph Canvas Packet](../ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md)
- Inherited Secondary Regression Docs: [Track B Test Packet](../ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md)
- Execution Dependencies: `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P01_preferences_and_graphics_settings.md`

## Objective

- Add the expand-time collision solver, occupied-bounds computation, and grouped history wiring so a collapsed item can expand in place while nearby eligible objects are translated according to the new global settings.

## Preconditions

- `P01` is complete and the effective settings are available through the active host or scene preference path.
- The implementation base is current `main`.

## Execution Dependencies

- `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P01_preferences_and_graphics_settings.md`

## Target Subsystems

- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/collision_avoidance_ops.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/graph/comment_backdrop_geometry.py`
- `ea_node_editor/graph/transform_layout_ops.py`
- `ea_node_editor/graph/mutation_service.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_comment_backdrop_membership.py`
- `tests/test_comment_backdrop_collapse.py`
- `tests/test_graph_surface_input_contract.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/collision_avoidance_ops.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/graph/comment_backdrop_geometry.py`
- `ea_node_editor/graph/transform_layout_ops.py`
- `ea_node_editor/graph/mutation_service.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_comment_backdrop_membership.py`
- `tests/test_comment_backdrop_collapse.py`
- `tests/test_graph_surface_input_contract.py`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/P02_expand_collision_avoidance_WRAPUP.md`

## Source Public Entry Points

- `GraphSceneMutationHistory.set_node_collapsed`
- `selection_and_scope_ops.set_node_collapsed`
- grouped layout update helpers in `graph_scene_mutation_history.py`
- comment backdrop membership and bounds helpers
- graph-scene payload projection for expanded occupied bounds

## Regression Public Entry Points

- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_comment_backdrop_membership.py`
- `tests/test_comment_backdrop_collapse.py`
- `tests/test_graph_surface_input_contract.py`

## State Owner

- Collapse state remains owned by the graph model and mutation boundary. This packet may compute transient collision-avoidance geometry and apply grouped position mutations, but it must not invent parallel persistence state or restore journals.

## Allowed Dependencies

- [PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md](../../../../PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md)
- [GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md](./GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md)
- [Graph Scene Packet](../ui_context_scalability_refactor/GRAPH_SCENE_PACKET.md)
- [Graph Canvas Packet](../ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md)
- [Graph Surface Test Packet](../ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md)
- [Track B Test Packet](../ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md)

## Required Invariants

- Collision avoidance runs only on `collapsed -> expanded` transitions.
- The expanded item remains fixed; other eligible objects move.
- Expand plus translation is one grouped history action and one undo step.
- Re-collapse does not restore prior auto-moved positions.
- `local` and `unbounded` reach behavior must honor the locked defaults and settings surface from `P01`.
- Comment occupied bounds must include the backdrop and its direct current members without rearranging internal layout.

## Forbidden Shortcuts

- Do not persist auto-move metadata into `.sfe` or app preferences beyond the settings surface already introduced in `P01`.
- Do not introduce a new lock, pin, or frozen-object model in this packet.
- Do not implement comment peek mode here.
- Do not solve collisions by moving the expanding item itself.

## Required Tests

- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_comment_backdrop_membership.py`
- `tests/test_comment_backdrop_collapse.py`
- `tests/test_graph_surface_input_contract.py`

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_comment_backdrop_membership.py tests/test_comment_backdrop_collapse.py tests/test_graph_surface_input_contract.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q
```

## Expected Artifacts

- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/collision_avoidance_ops.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/graph/comment_backdrop_geometry.py`
- `ea_node_editor/graph/transform_layout_ops.py`
- `ea_node_editor/graph/mutation_service.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_comment_backdrop_membership.py`
- `tests/test_comment_backdrop_collapse.py`
- `tests/test_graph_surface_input_contract.py`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/P02_expand_collision_avoidance_WRAPUP.md`

## Acceptance Criteria

- Expanding a collapsed item can trigger collision avoidance according to the settings introduced in `P01`.
- The expanding item remains fixed and nearby eligible objects move within one grouped history action.
- Comment occupied-bounds handling follows the locked direct-member contract.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P02`. Do not start `P03` in the same thread.
- `P03` inherits the collision-avoidance behavior and adds comment-only peek mode on top of the existing scene and canvas contracts.
