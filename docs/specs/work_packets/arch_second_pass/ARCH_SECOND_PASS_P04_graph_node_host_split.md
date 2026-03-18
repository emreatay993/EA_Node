# ARCH_SECOND_PASS P04: GraphNodeHost Split

## Objective
- Split `GraphNodeHost.qml` host-routing, chrome, and hit-testing responsibilities into focused helpers/components so the host stops acting as the single giant nexus for surface interaction, ports, and rendering glue.

## Preconditions
- `P00` through `P03` are marked `PASS` in [ARCH_SECOND_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_STATUS.md).
- No later `ARCH_SECOND_PASS` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- new packet-owned helper components or JS modules under `ea_node_editor/ui_qml/components/graph/`
- graph-surface host regression tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/**`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`

## Required Behavior
- Separate packet-owned host gesture routing, embedded-interactive-rect hit testing, and node chrome/port presentation concerns into focused helpers/components.
- Keep current host/body drag/select/open/context behavior, surface ownership rules, and surface-loader contracts stable.
- Preserve the graph-surface input routing model introduced by `GRAPH_SURFACE_INPUT`.
- Avoid reopening `GraphCanvas.qml` or heavy surface components except for narrow compatibility fallout inside the packet write scope.

## Non-Goals
- No metrics unification or `GraphMediaPanelSurface.qml` decomposition yet; `P05` owns that.
- No graph-scene core refactor yet.
- No shell bridge contract changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host tests.test_graph_surface_input_contract -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host.PassiveGraphSurfaceHostTests.test_graph_node_host_routes_body_click_open_and_context_from_below_surface_layer -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_second_pass/P04_graph_node_host_split_WRAPUP.md`

## Acceptance Criteria
- `GraphNodeHost.qml` becomes materially less monolithic without changing the current host/surface contracts.
- Current host/input-routing regression coverage passes.
- Packet-owned helper boundaries are easier to test and reason about than the previous all-in-one host file.

## Handoff Notes
- `P05` can assume host responsibilities are better factored before unifying metrics and decomposing heavy panes.
- Do not reintroduce invisible click-swallowing overlays or compatibility-only hover proxies.
