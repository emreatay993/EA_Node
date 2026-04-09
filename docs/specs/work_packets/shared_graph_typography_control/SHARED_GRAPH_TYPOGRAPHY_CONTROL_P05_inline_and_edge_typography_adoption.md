# SHARED_GRAPH_TYPOGRAPHY_CONTROL P05: Inline and Edge Typography Adoption

## Objective
- Move inline property labels, inline status chips, and flow-edge labels/pills onto the shared typography role contract while inheriting the earlier QML preference regression anchor instead of leaving duplicate or stale typography assertions behind.

## Preconditions
- `P04` is marked `PASS` in [SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md](./SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md).
- No later `SHARED_GRAPH_TYPOGRAPHY_CONTROL` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_flow_edge_labels.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_flow_edge_labels.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`
- `docs/specs/work_packets/shared_graph_typography_control/P05_inline_and_edge_typography_adoption_WRAPUP.md`

## Required Behavior
- Replace the hardcoded inline-property label and inline status-chip font sizes and weights in `GraphInlinePropertiesLayer.qml` with the packet-owned shared typography roles from `P03`.
- Replace the hardcoded flow-edge label and flow-edge pill font sizes and weights in `EdgeFlowLabelLayer.qml` with the packet-owned shared typography roles from `P03`.
- Keep existing edge-label text content, anchor behavior, pill geometry intent, selection behavior, and output-mode semantics stable while only the typography source changes.
- Preserve passive-authoritative `visual_style.font_size` / `font_weight` precedence on any passive text path that already owns its typography through the host/theme path, even while touched inline or edge-adjacent surfaces adopt the shared graph chrome roles.
- Update the inherited `tests/graph_track_b/qml_preference_bindings.py` regression anchor instead of duplicating the same shared-role assertions in a new later-only test.
- Add packet-owned regression tests whose names include `graph_typography_inline_edge` so the targeted verification commands below remain stable.

## Non-Goals
- No standard node header, port, or elapsed-footer changes beyond consuming the already-landed shared contract from `P04`.
- No Graphics Settings dialog control yet.
- No requirement, QA-matrix, or traceability refresh yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_inline.py tests/graph_track_b/qml_preference_bindings.py -k graph_typography_inline_edge --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/graph_track_b/qml_preference_bindings.py -k graph_typography_inline_edge --ignore=venv -q`
3. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k graph_typography_inline_edge --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py -k graph_typography_inline_edge --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/shared_graph_typography_control/P05_inline_and_edge_typography_adoption_WRAPUP.md`

## Acceptance Criteria
- Inline property labels and status chips consume the shared typography roles rather than hardcoded literals.
- Flow-edge labels and pills consume the shared typography roles rather than hardcoded literals.
- Passive-authoritative `font_size` / `font_weight` paths remain authoritative where they already applied before this packet.
- The inherited QML preference regression anchor remains current, and the packet-owned `graph_typography_inline_edge` regressions pass.

## Handoff Notes
- `P06` adds the end-user Graphics Settings control and should reuse the already-established shared-role behavior instead of reopening consumer-level typography math.
- Any later packet that changes inline or edge typography behavior must inherit and update `tests/test_graph_surface_input_inline.py`, `tests/test_flow_edge_labels.py`, `tests/graph_surface/passive_host_interaction_suite.py`, and `tests/graph_track_b/qml_preference_bindings.py`.
