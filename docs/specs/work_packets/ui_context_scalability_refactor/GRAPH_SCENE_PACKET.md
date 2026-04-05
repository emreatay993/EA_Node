# Graph Scene Packet

Baseline packet: `P03 Graph Scene Bridge Packet Split`.

Use this contract when a change affects scoped graph mutation, graph-scene payload projection, scene bridge exports, selection policy, pending surface actions, or graph-theme-aware payload building before data reaches QML.

## Owner Files

- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/__init__.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/policy_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/read_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`

## Public Entry Points

- `GraphSceneBridge`
- `GraphSceneReadBridge`
- `GraphSceneCommandBridge`
- `GraphScenePolicyBridge`
- The curated `ea_node_editor.ui_qml.graph_scene` package exports used by `graph_scene_bridge.py`

## State Owner

- `GraphModel` remains the authoritative graph state.
- `GraphSceneBridge` owns the scene-facing composition surface that binds model, registry, runtime history, payload cache, and graph-theme projection together.
- `GraphSceneMutationHistory`, `GraphSceneScopeSelection`, `GraphScenePayloadBuilder`, and pending surface action state own scene-local mutation grouping and payload projection details behind that bridge.

## Allowed Dependencies

- Graph-scene packet code may depend on graph domain models, mutation-service helpers, runtime history, graph theme projection, PDF/media boundary adapters, and graph-surface metrics inputs.
- Graph-scene packet code may publish bridge objects to shell or canvas consumers, but those consumers should use the documented bridge surfaces rather than internal helpers.
- Packet-owned tests may tighten scene or graph-surface regression anchors when payload names or scope-selection rules change.

## Invariants

- `graph_scene_bridge.py` stays a thin export and composition surface.
- Packet-owned support logic lives under `ea_node_editor/ui_qml/graph_scene/` or focused graph-scene helpers rather than inside one omnibus bridge file.
- Scene edits remain scope-aware and mutation-history-aware.
- Payload building stays the only packet-owned path that normalizes theme, backdrop, port, and media payload details before QML consumes them.

## Forbidden Shortcuts

- Do not mutate graph state directly from QML without going through the command bridge and mutation-history path.
- Do not reintroduce packet-owned host fallbacks or new raw QML globals while changing graph-scene support code.
- Do not move payload shaping into unrelated shell or canvas files when the graph-scene packet owns it.
- Do not reopen `graph_scene_bridge.py` as a broad state bucket.

## Required Tests

- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_main_window_shell.py`
