# GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT P02: Gap Break Renderer Adoption

## Objective

- Implement deterministic gap-break crossing decoration in the edge renderer while preserving the original edge geometry for interaction, culling, arrowheads, and labels.

## Preconditions

- `P01` is complete and `GraphCanvas.qml` plus `EdgeLayer.qml` already receive the effective `edgeCrossingStyle`.
- The implementation base is current `main`.

## Execution Dependencies

- `GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P01_edge_crossing_preference_pipeline.md`

## Target Subsystems

- `ea_node_editor/ui_qml/components/graph/EdgeMath.js`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_flow_edge_labels.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/graph/EdgeMath.js`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_flow_edge_labels.py`
- `docs/specs/work_packets/global_gap_break_edge_crossing_variant/P02_gap_break_renderer_adoption_WRAPUP.md`
- `docs/specs/work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md`

## Required Behavior

- Compute crossing decoration from visible edge snapshots inside `EdgeLayer.qml`; do not mutate stored graph state.
- Run the internal crossing-decoration pass only when `edgeCrossingStyle === "gap_break"` and the canvas is in full-fidelity rendering.
- Support `edge_crossing_style === "none"` as the no-op baseline and `edge_crossing_style === "gap_break"` as the decorated mode.
- Build the final draw order before crossing detection: non-selected edges in their existing payload order, then previewed and selected edges appended in their existing relative order.
- Implement deterministic over/under ordering from that draw order so previewed and selected edges render over non-previewed and non-selected edges, with remaining ties resolved by the existing payload order.
- Extend `EdgeMath.js` with the packet-owned helpers needed to sample bezier routes into polylines, reuse pipe routes directly, broad-phase prune by intersecting bounds, detect segment intersections, reject endpoint or near-anchor crossings, and merge nearby break ranges on the under edge.
- Express gap sizing in screen space and convert it to scene units by zoom so the visible break remains stable across zoom levels.
- Internal visible-edge snapshots may gain non-persistent `crossingBreaks` metadata, or equivalent packet-owned rendering metadata, for renderer and test use only.
- Render under edges as multiple subpaths with skipped ranges near crossing points, then render over edges normally.
- Keep edge hit testing, culling, arrowheads, and label anchors based on the original undecorated path geometry.
- Disable crossing decoration when performance policy is in `max_performance` mode or in any transient degraded-rendering window already exposed to the packet-owned renderer path.
- Add regression coverage for `none` versus `gap_break`, break metadata appearing only on under edges, deterministic crossing order, pipe/pipe and bezier-involved crossings, interaction geometry preservation, and performance suppression.

## Non-Goals

- No new settings or dialog work; `P01` already owns preference plumbing.
- No `.sfe` persistence changes or per-edge style fields.
- No requirements-doc, QA-matrix, or traceability updates in this packet.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py tests/test_flow_edge_labels.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q
```

## Expected Artifacts

- `ea_node_editor/ui_qml/components/graph/EdgeMath.js`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_flow_edge_labels.py`
- `docs/specs/work_packets/global_gap_break_edge_crossing_variant/P02_gap_break_renderer_adoption_WRAPUP.md`

## Acceptance Criteria

- `gap_break` decoration appears only when the global style is enabled and fidelity policy allows it.
- Break metadata or equivalent renderer-side break ranges appear only on under edges.
- Crossing order is deterministic and matches the packet contract for previewed/selected edges versus the remaining payload order.
- `edgeAtScreen()` remains stable across zoom because edge interaction geometry still follows the original edge path.
- Flow labels, label anchors, and arrowhead placement still follow the original edge path.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P02`. Do not start `P03` in the same thread.
- `P03` owns QA publication, requirement updates, and traceability closeout for this shipped behavior.
