# SHARED_GRAPH_TYPOGRAPHY_CONTROL P04: Standard Node Chrome Typography Adoption

## Objective
- Move standard node headers, standard port labels, exec-arrow labels, and the retained elapsed footer onto the shared typography role contract while preserving passive-authoritative font paths where they already exist today.

## Preconditions
- `P03` is marked `PASS` in [SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md](./SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md).
- No later `SHARED_GRAPH_TYPOGRAPHY_CONTROL` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml`
- `tests/test_shell_run_controller.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml`
- `tests/test_shell_run_controller.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`
- `docs/specs/work_packets/shared_graph_typography_control/P04_standard_node_chrome_typography_adoption_WRAPUP.md`

## Required Behavior
- Replace the hardcoded standard-node title and badge sizes and weights in `GraphNodeHeaderLayer.qml` with the packet-owned shared typography roles from `P03`.
- Replace the hardcoded standard port-label and exec-arrow label sizes and weights in `GraphNodePortsLayer.qml` with the packet-owned shared typography roles from `P03`.
- Replace the hardcoded elapsed-footer size in `GraphNodeHost.qml` with the packet-owned shared typography role from `P03` while preserving the existing formatter, object names, and timing semantics retained from `PERSISTENT_NODE_ELAPSED_TIMES`.
- Preserve the existing passive-authoritative `visual_style.font_size` and `visual_style.font_weight` behavior in `GraphNodeHostTheme.qml` and any host-layer consumers that already use those packet-external passive paths.
- Keep the global typography token additive for standard graph chrome on passive nodes only where no passive-specific font path already exists.
- Add packet-owned regression tests whose names include `graph_typography_host_chrome` so the targeted verification commands below remain stable.

## Non-Goals
- No inline property label or flow-edge label adoption yet.
- No passive-style dialog/schema changes.
- No Graphics Settings dialog control yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k graph_typography_host_chrome --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k graph_typography_host_chrome --ignore=venv -q`
3. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py -k graph_typography_host_chrome --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k graph_typography_host_chrome --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/shared_graph_typography_control/P04_standard_node_chrome_typography_adoption_WRAPUP.md`

## Acceptance Criteria
- Standard node titles, badges, port labels, exec-arrow labels, and elapsed footer consume the shared typography roles rather than packet-local hardcoded size or weight literals.
- Passive `visual_style.font_size` / `font_weight` authority still wins on the paths that already used it before this packet.
- The retained elapsed-footer semantics from `PERSISTENT_NODE_ELAPSED_TIMES` stay intact while only the typography source changes.
- The packet-owned `graph_typography_host_chrome` regressions pass.

## Handoff Notes
- `P05` inherits `tests/graph_track_b/qml_preference_bindings.py` because inline and edge typography adoption changes another set of shared-role consumers in the same QML preference path.
- Any later packet that changes elapsed-footer typography semantics, passive-authoritative font precedence, or the shared role usage for titles/ports must inherit and update `tests/test_shell_run_controller.py`, `tests/graph_surface/passive_host_interaction_suite.py`, and `tests/graph_track_b/qml_preference_bindings.py`.
