# Track B Test Packet

Baseline packet: `P07 Track B Test Packetization`.

Use this contract when a UI change touches Track-B QML preference bindings, scene-model or graph-scene coverage consumed by Track B, theme or viewport helpers, or the stable Track-B regression entrypoints that prove those seams.

## Source Packet Docs

- [Graph Scene Packet](./GRAPH_SCENE_PACKET.md)
- [Graph Canvas Packet](./GRAPH_CANVAS_PACKET.md)
- [Edge Rendering Packet](./EDGE_RENDERING_PACKET.md)

## Owner Files

- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/graph_track_b/scene_and_model.py`
- `tests/graph_track_b/qml_support.py`
- `tests/graph_track_b/theme_support.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`
- `tests/graph_track_b/qml_preference_performance_suite.py`
- `tests/graph_track_b/scene_model_graph_model_suite.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`

## Public Entry Points

- `tests/graph_track_b/qml_preference_bindings.py` is the stable Track-B QML preference regression entrypoint.
- `tests/graph_track_b/scene_and_model.py` is the stable Track-B scene-model entrypoint and compatibility export surface for packet-external helpers.
- The focused Track-B suite modules own the detailed rendering, performance, graph-model, and graph-scene cases behind those entrypoints.

## State Owner

- `tests/graph_track_b/qml_support.py` owns the shared QML subprocess harness and helper builders reused across Track-B preference coverage.
- `tests/graph_track_b/theme_support.py` owns the theme fixtures, bridge helpers, and color-token helpers reused across Track-B scene-model coverage.
- The focused suite modules own detailed assertions; the stable entrypoints aggregate them.

## Allowed Dependencies

- This regression packet may depend on the public graph-scene, graph-canvas, and edge-rendering seams documented in the linked source packet docs.
- This regression packet may reuse packet-owned helpers under `tests/graph_track_b/` when they remain import surfaces rather than local umbrella bodies.
- Packet-external consumers such as `tests/graph_track_b/runtime_history.py`, `tests/graph_track_b/viewport.py`, `tests/test_graph_track_b.py`, and `tests/test_flow_edge_labels.py` may inherit these exports, but packet-owned Track-B regressions stay here first.

## Invariants

- `tests/graph_track_b/qml_preference_bindings.py` and `tests/graph_track_b/scene_and_model.py` stay thin stable entrypoints.
- Shared QML and theme helpers stay centralized in `tests/graph_track_b/qml_support.py` and `tests/graph_track_b/theme_support.py`.
- Compatibility exports consumed by packet-external Track-B helpers update together with the focused suites when a helper moves.
- Detailed Track-B rendering, performance, graph-model, and graph-scene regressions stay in the focused suite modules instead of regrowing in the stable entrypoints.

## Forbidden Shortcuts

- Do not regrow the stable entrypoint files into local umbrella bodies.
- Do not duplicate QML subprocess or theme helper logic outside the shared Track-B support files.
- Do not move packet-owned Track-B assertions back into broader regression files when the focused suite modules can carry the proof.

## Required Tests

- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/graph_track_b/scene_and_model.py`
- `tests/test_graph_track_b.py`
- `tests/test_flow_edge_labels.py`
