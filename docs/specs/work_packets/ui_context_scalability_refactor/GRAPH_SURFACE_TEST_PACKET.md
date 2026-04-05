# Graph Surface Test Packet

Baseline packet: `P06 Graph Surface Test Packetization`.

Use this contract when a UI change touches graph-surface host interaction, GraphCanvas input routing, inline surface editors, media or scope probes, or the stable regression entrypoints that prove those seams.

## Source Packet Docs

- [Graph Scene Packet](./GRAPH_SCENE_PACKET.md)
- [Graph Canvas Packet](./GRAPH_CANVAS_PACKET.md)
- [Edge Rendering Packet](./EDGE_RENDERING_PACKET.md)
- [Viewer Packet](./VIEWER_PACKET.md)

## Owner Files

- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/graph_surface/__init__.py`
- `tests/graph_surface/environment.py`
- `tests/graph_surface/passive_host_boundary_suite.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/graph_surface/pointer_and_modal_suite.py`
- `tests/graph_surface/inline_editor_suite.py`
- `tests/graph_surface/media_and_scope_suite.py`

## Public Entry Points

- `tests/test_passive_graph_surface_host.py` is the stable host-regression entrypoint.
- `tests/test_graph_surface_input_contract.py` is the stable graph-surface input-contract entrypoint.
- `tests/graph_surface/__init__.py` is the curated export surface for the focused suites behind those entrypoints.

## State Owner

- `tests/graph_surface/environment.py` owns the shared QML probe harness, subprocess retry guard, and common graph-surface runtime helpers reused across the focused suites.
- The focused suite modules own detailed host, boundary, pointer, inline-editor, and media or scope assertions; the stable entrypoints only import them.

## Allowed Dependencies

- This regression packet may depend on the public graph-scene, graph-canvas, edge-rendering, and viewer seams documented in the linked source packet docs.
- This regression packet may reuse packet-owned helpers under `tests/graph_surface/` when they stay import surfaces rather than local umbrella bodies.
- Higher-level anchors such as `tests/test_graph_surface_input_controls.py` and `tests/test_graph_surface_input_inline.py` may inherit this packet's focused suites, but packet-owned graph-surface regressions stay here first.

## Invariants

- `tests/test_passive_graph_surface_host.py` and `tests/test_graph_surface_input_contract.py` stay thin stable entrypoints.
- Shared QML probe and retry behavior stays centralized in `tests/graph_surface/environment.py`.
- Detailed host and input regressions stay in the focused suite modules instead of regrowing in the stable entrypoints.
- Packet-owned graph-surface exports remain available through `tests.graph_surface`.

## Forbidden Shortcuts

- Do not regrow the stable entrypoint files into local umbrella bodies.
- Do not duplicate QML probe setup, retry guards, or shared environment helpers outside `tests/graph_surface/environment.py`.
- Do not bypass the shared offscreen retry path for packet-owned graph-surface probes.

## Required Tests

- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
