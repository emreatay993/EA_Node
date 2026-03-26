# ARCHITECTURE_REFACTOR P04: Graph Boundary Adapters

## Objective
- Remove direct UI/QML imports from graph mutation paths by introducing explicit boundary adapters for geometry and preview-policy concerns, then add a narrow architecture-boundary guardrail so graph-layer imports do not regress back toward UI/QML helpers.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/`
- `ea_node_editor/ui/pdf_preview_provider.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_port_labels.py`
- `tests/test_comment_backdrop_membership.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_flow_edge_labels.py`

## Conservative Write Scope
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/`
- `ea_node_editor/ui/pdf_preview_provider.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_port_labels.py`
- `tests/test_comment_backdrop_membership.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_flow_edge_labels.py`
- `docs/specs/work_packets/architecture_refactor/P04_graph_boundary_adapters_WRAPUP.md`

## Required Behavior
- Remove graph-layer imports of preview and QML geometry helpers from mutation-time paths.
- Introduce explicit adapters or application-layer inputs for node geometry measurement and PDF page normalization instead of reaching into UI modules directly from graph code.
- Add or update a packet-owned architecture-boundary regression that proves graph modules in this seam do not import UI/QML helpers directly.
- Preserve current persisted graph document shape and current authoring behavior while moving the dependency boundary.
- Limit packet-owned UI/QML changes to call-site wiring needed to satisfy the new graph boundary.

## Non-Goals
- No full invariant or normalization consolidation yet.
- No serializer/migration policy rewrite yet.
- No canvas/scene hotspot decomposition yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_port_labels.py tests/test_comment_backdrop_membership.py tests/test_pdf_preview_provider.py tests/test_flow_edge_labels.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P04_graph_boundary_adapters_WRAPUP.md`

## Acceptance Criteria
- Graph mutation code no longer depends directly on UI preview or QML geometry helpers.
- Boundary adapters are explicit and test-covered by the packet-owned regression anchors, including the graph import-boundary guardrail.
- The packet-owned verification command passes.

## Handoff Notes
- `P05` will centralize invariant policy on top of these cleaner graph boundaries; do not hide policy consolidation inside this packet.
- `P10` may extend the architecture-boundary guardrail to DPF or built-in node seams when packet-owned node-layer imports move.
