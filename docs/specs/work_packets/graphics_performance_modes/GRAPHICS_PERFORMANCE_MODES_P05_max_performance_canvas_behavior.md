# GRAPHICS_PERFORMANCE_MODES P05: Max Performance Canvas Behavior

## Objective
- Apply the whole-canvas `Max Performance` interaction policy for pan/zoom and mutation bursts while preserving `Full Fidelity` visuals and restoring full idle fidelity automatically.

## Preconditions
- `P00` through `P04` are marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- targeted canvas-mode regression tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_flow_edge_labels.py`
- `docs/specs/work_packets/graphics_performance_modes/P05_max_performance_canvas_behavior_WRAPUP.md`

## Required Behavior
- Consume the centralized policy outputs from `P04` so `Max Performance` affects the whole canvas during active pan/zoom and structural mutation bursts.
- During the degraded window, allow temporary whole-canvas simplifications including node-shadow suppression, more aggressive edge-label simplification/hiding, reduced or frozen grid work, and minimap refresh reduction or deferment.
- Reuse cached/snapshot-style node presentation during the degraded window wherever the existing host/cache path allows it, while keeping idle visuals fully restored after the settle timer expires.
- Keep `Full Fidelity` visually unchanged aside from the invisible optimizations already landed in `P04`.
- Preserve public `graphCanvas` object discoverability and methods.
- Add or update focused tests that lock both `full_fidelity` and `max_performance` behavior across the degraded window and idle recovery.

## Non-Goals
- No Node SDK or plugin render-quality metadata yet. `P06` owns that.
- No proxy-surface hook or built-in heavy-media adoption yet. `P07` and `P08` own those.
- No benchmark/report or docs work yet. `P09` and `P10` own those.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -k "max_performance" -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "max_performance" -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -k "max_performance" -q`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P05_max_performance_canvas_behavior_WRAPUP.md`

## Acceptance Criteria
- `Max Performance` applies a documented degraded-window whole-canvas policy during pan/zoom and mutation bursts.
- `Full Fidelity` remains visually unchanged in ordinary use.
- Idle appearance fully recovers automatically after the settle timer.
- Focused canvas-mode regressions pass without breaking public canvas contracts.

## Handoff Notes
- Record the exact degraded-window behaviors that landed in the wrap-up so `P08` and `P09` can benchmark/document the right expectations.
- If any simplification had to be weaker than planned to preserve UX, note that plainly so later desktop validation interprets the results correctly.
