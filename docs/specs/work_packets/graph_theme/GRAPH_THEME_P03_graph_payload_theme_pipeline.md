# GRAPH_THEME P03: Graph Payload Theme Pipeline

## Objective
- Move graph semantic colors out of hard-coded presenter helpers and into the graph-theme presentation pipeline.

## Preconditions
- `P02` is marked `PASS` in [GRAPH_THEME_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_theme/GRAPH_THEME_STATUS.md).
- `graphThemeBridge` exists as the canonical runtime graph-theme surface.

## Target Subsystems
- `ea_node_editor/ui/graph_theme/presentation.py` (new if needed)
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `tests/test_graph_track_b.py`
- `tests/test_graph_theme_shell.py`

## Required Behavior
- Add graph-theme presentation helpers for:
  - category accent resolution
  - port-kind color resolution
  - edge default color resolution
  - edge warning color resolution
- Update `GraphSceneBridge` to consume the resolved graph-theme presentation helpers instead of hard-coded graph color rules.
- Update node payload accent generation and edge payload colors to use graph-theme helpers.
- Rebuild graph payloads when the active graph theme changes.
- Keep theme shaping in the presenter/bridge layer rather than graph-model dataclasses.

## Non-Goals
- No QML node/edge consumption changes yet.
- No graph-model schema changes.
- No canvas chrome changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_graph_theme_shell -v`

## Acceptance Criteria
- Node accents and edge colors come from the graph-theme presentation layer rather than hard-coded helpers.
- Graph payloads refresh when the active graph theme changes.
- `.sfe` persistence and graph-model dataclasses remain unchanged.

## Handoff Notes
- `P04` migrates `NodeCard.qml` and `EdgeLayer.qml` to consume the new graph-theme bridge while preserving GraphCanvas contracts.
