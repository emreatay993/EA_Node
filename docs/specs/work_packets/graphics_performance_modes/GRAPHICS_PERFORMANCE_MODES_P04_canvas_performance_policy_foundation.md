# GRAPHICS_PERFORMANCE_MODES P04: Canvas Performance Policy Foundation

## Objective
- Centralize the resolved canvas performance policy for `Full Fidelity` versus `Max Performance`, add structural mutation-burst timing, and land only invisible full-fidelity hot-path optimizations.

## Preconditions
- `P00` through `P03` are marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- a packet-owned performance-policy helper under `ea_node_editor/ui_qml/components/graph_canvas/`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- targeted canvas interaction/performance-state regression tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/*.js`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_flow_edge_labels.py`
- `docs/specs/work_packets/graphics_performance_modes/P04_canvas_performance_policy_foundation_WRAPUP.md`

## Required Behavior
- Introduce one centralized helper or policy owner that resolves canvas behavior from the persisted mode plus transient activity state, rather than scattering mode checks across unrelated QML files.
- Track both viewport interaction activity and structural mutation bursts, with mutation-burst settle timing reusing the existing `150 ms` idle window unless a packet-owned private equivalent is clearly safer.
- Expose resolved policy outputs that later packets can consume for grid, minimap, edge-label, shadow, and snapshot/proxy behavior.
- Keep `Full Fidelity` free of visible quality cuts in this packet.
- Land only invisible hot-path improvements that do not change user-visible output, such as removing unused edge-label hit-test work or another equivalent documented edge-layer cleanup.
- Add or update deterministic tests for policy-state activation/recovery and the full-fidelity non-degraded baseline.

## Non-Goals
- No whole-canvas max-performance simplification policy yet. `P05` owns that.
- No Node SDK render-quality contract yet. `P06` owns that.
- No built-in heavy-surface proxy adoption yet. `P08` owns that.
- No benchmark/report or docs work yet. `P09` and `P10` own those.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -k "performance_policy or mutation_burst" -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "performance_policy or mutation_burst" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P04_canvas_performance_policy_foundation_WRAPUP.md`

## Acceptance Criteria
- One documented policy owner resolves canvas performance behavior from mode + transient activity state.
- Structural mutation bursts participate in the same degraded-window timing model that later packets will consume.
- Full-fidelity behavior remains visually unchanged while the invisible hot-path cleanup lands.
- Focused canvas interaction and edge-label regressions pass.

## Handoff Notes
- Record the final policy-helper location and exported inputs/outputs in the wrap-up so `P05`, `P07`, and `P08` reuse it instead of re-deriving activity state.
- If the invisible hot-path cleanup changes an edge-label internal assumption, document that clearly for later packets.
