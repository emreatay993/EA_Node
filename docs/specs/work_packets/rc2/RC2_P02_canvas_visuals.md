# RC2 P02: Canvas and Graph Visuals

## Objective
- Upgrade scene background, node chrome, edge visuals, and zoom-level detail behavior to Stitch parity while preserving performance requirements.

## Inputs
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/gui/1_stitch_engineering_node_editor_workspace.zip`

## Allowed Files
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/viewport_bridge.py`
- `tests/test_graph_track_b.py`

## Do Not Touch
- `ea_node_editor/execution/*`
- `ea_node_editor/persistence/*`

## Verification
1. `venv\Scripts\python -m unittest tests.test_graph_track_b -v`
2. `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`

## Output Artifacts
- `docs/specs/perf/rc2/canvas_nodes.png`

## Merge Gate
- Graph tests pass.
- Perf harness stays under target thresholds.
