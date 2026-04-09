# SHARED_GRAPH_TYPOGRAPHY_CONTROL P03: Canvas Typography Contract and Metrics

## Objective
- Expose the canvas-facing `graphLabelPixelSize` binding, define one shared graph typography size-and-weight role contract for later QML consumers, and align deterministic scene/payload text metrics with that contract before renderer-facing chrome adoption begins.

## Preconditions
- `P02` is marked `PASS` in [SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md](./SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md).
- No later `SHARED_GRAPH_TYPOGRAPHY_CONTROL` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph/GraphSharedTypography.qml`
- `ea_node_editor/ui_qml/graph_geometry/standard_metrics.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph/GraphSharedTypography.qml`
- `ea_node_editor/ui_qml/graph_geometry/standard_metrics.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`
- `docs/specs/work_packets/shared_graph_typography_control/P03_canvas_typography_contract_and_metrics_WRAPUP.md`

## Required Behavior
- Add the packet-owned canvas/root binding `graphLabelPixelSize` in `GraphCanvasRootBindings.qml` and source it from the Python-side `graphics_graph_label_pixel_size` property added in `P02`.
- Introduce one shared QML-accessible typography source at `ea_node_editor/ui_qml/components/graph/GraphSharedTypography.qml`.
- Define stable packet-owned role pixel-size properties on that shared source for later packets to consume:
  - `nodeTitlePixelSize`
  - `portLabelPixelSize`
  - `elapsedFooterPixelSize`
  - `inlinePropertyPixelSize`
  - `badgePixelSize`
  - `edgeLabelPixelSize`
  - `edgePillPixelSize`
  - `execArrowPortPixelSize`
- Define stable packet-owned role font-weight properties on that shared source for later packets to consume wherever graph chrome still hardcodes font boldness today:
  - `nodeTitleFontWeight`
  - `portLabelFontWeight`
  - `inlinePropertyFontWeight`
  - `badgeFontWeight`
  - `edgeLabelFontWeight`
  - `edgePillFontWeight`
  - `execArrowPortFontWeight`
- Derive those role properties from `graphLabelPixelSize` and the locked typography hierarchy in the manifest instead of hardcoded consumer-local math.
- Update deterministic text-width and standard-node metric calculations so any packet-owned title/label width estimation that depends on standard graph chrome stops assuming the old hardcoded literal sizes.
- Reuse an existing payload refresh or revision seam so typography preference changes can refresh scene/payload consumers without adding a second typography-only invalidation channel.
- Add packet-owned regression tests whose names include `graph_typography_qml_contract` so the targeted verification commands below remain stable.

## Non-Goals
- No end-user Graphics Settings control yet.
- No direct adoption in `GraphNodeHeaderLayer.qml`, `GraphNodePortsLayer.qml`, `GraphInlinePropertiesLayer.qml`, `GraphNodeHost.qml`, or `EdgeFlowLabelLayer.qml` yet beyond any contract plumbing strictly required to keep metrics coherent.
- No passive-style override behavior change.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py tests/graph_track_b/qml_preference_bindings.py -k graph_typography_qml_contract --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py -k graph_typography_qml_contract --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/shared_graph_typography_control/P03_canvas_typography_contract_and_metrics_WRAPUP.md`

## Acceptance Criteria
- `GraphCanvasRootBindings.qml` exposes `graphLabelPixelSize` from the packet-owned Python bridge property.
- `GraphSharedTypography.qml` defines the stable shared role pixel-size and font-weight contract used by later packets.
- Deterministic standard-node or scene-payload text metrics that depend on graph chrome adopt the same role-based sizes instead of stale hardcoded literals.
- The packet-owned `graph_typography_qml_contract` regressions pass.

## Handoff Notes
- `P04` and `P05` consume the role-property names defined here. Do not rename those properties after this packet without inheriting and updating `tests/main_window_shell/bridge_qml_boundaries.py` and `tests/graph_track_b/qml_preference_bindings.py`.
- If a later packet discovers another deterministic metric seam that must move with the shared role sizes, that later packet inherits this metric contract and updates `graph_scene_payload_builder.py` or `standard_metrics.py` in-scope.
