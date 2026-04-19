## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/addon-manager-backend-preparation/p04-locked-node-graph-host-and-mockup-b-visuals`
- Commit Owner: `worker`
- Commit SHA: `964b8129cb1e94ada19bf3437a37eb5d2b4f47ba`
- Changed Files: `docs/specs/work_packets/addon_manager_backend_preparation/P04_locked_node_graph_host_and_mockup_b_visuals_WRAPUP.md`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`, `ea_node_editor/ui_qml/graph_geometry/standard_metrics.py`, `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_graph_surface_input_controls.py`, `tests/test_passive_graph_surface_host.py`
- Artifacts Produced: `docs/specs/work_packets/addon_manager_backend_preparation/P04_locked_node_graph_host_and_mockup_b_visuals_WRAPUP.md`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`, `ea_node_editor/ui_qml/graph_geometry/standard_metrics.py`, `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_graph_surface_input_controls.py`, `tests/test_passive_graph_surface_host.py`

- Moved locked-node authority into `GraphNodeHost.qml`, so `nodeData.read_only` and `nodeData.unresolved` now gate title editing, surface actions, common actions, destructive actions, drag and resize affordances, and manager-only locked placeholder behavior at the host boundary.
- Added the packet's Mockup B missing-add-on presentation across the host stack: muted locked header treatment, dashed accent stripe, `LOCKED` chip, collapsed `Requires add-on` placeholder ribbon with add-on details, manager affordance, and locked input and output port glyphs while preserving node silhouette and port positions.
- Routed the locked placeholder escape hatch through the existing P02 seam by sending common-action, context-menu, and placeholder-button requests to `addonManagerBridge.requestOpen(focus_addon_id)` when the missing add-on exposes a focus id.
- Hardened the graph canvas surface bridge against read-only mutation attempts so property commits, inline edits, crop edits, color picks, and browse-path requests short-circuit before reaching the scene or shell bridge for locked placeholders.
- Preserved the public `GraphCanvas.qml` idle-performance window at `interactionIdleDelayMs: 2000` while introducing a packet-local `150 ms` transient recovery path for viewport interaction and mutation-burst settle timers, clearing the inherited wheel-zoom and max-performance recovery regressions without regressing the longer-lived FPS-oriented idle budget.
- Split `resize_node()` from `set_node_geometry()` in the scene mutation boundary so explicit resize operations still clamp to the surface minimums, while live geometry commits preserve the emitted x/y/width/height contract used by the edge layer and passive-host resize path.
- Updated standard-node surface resolution so exact custom heights survive live-geometry commits, but stale custom heights that merely mirror an older default still normalize forward when header chrome grows, keeping the inherited typography and geometry contracts green.
- Refreshed packet-owned tests to cover the locked placeholder contract, manager-only node context menus, read-only bridge rejection, passive-host visual probes for the locked chip, stripe, ribbon, locked ports, and the inherited graph-canvas performance and live-resize geometry expectations that now pass on the packet branch.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py --ignore=venv -q` -> `118 passed, 18 subtests passed`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q` -> `21 passed, 18 subtests passed`
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree from `C:\w\ea_node_ed-p04-5d90ab` with `.\venv\Scripts\python.exe main.py` and use a project that contains locked missing-add-on nodes plus at least one standard graph node.

1. Locked placeholder host chrome
Action: open a graph containing a locked missing-add-on placeholder and inspect the node in both expanded and collapsed states.
Expected result: the node shows the muted Mockup B locked treatment, `LOCKED` badge, add-on requirement ribbon, locked port glyphs, and the Add-On Manager affordance when a focus id is available.

2. Locked read-only interaction boundary
Action: try title edits, inline property edits, destructive context actions, drag, and resize on the locked placeholder.
Expected result: mutation attempts are blocked at the host and bridge seams, manager-only actions remain available, and the node cannot be dragged or resized.

3. Graph canvas recovery and live resize smoke
Action: on an unlocked node, use mouse-wheel zoom in normal and max-performance modes, then resize a node while an edge is attached.
Expected result: transient degradation clears promptly after interaction, shadows and minimap/grid visibility recover, and the attached edge tracks the live resize geometry and final committed bounds.

## Residual Risks

- The required packet verification commands now pass, but the inherited suite still emits ambient ANSYS DPF deprecation warnings from third-party packages in the local venv.
- `interactionIdleDelayMs` remains the long idle-budget surface at `2000`; future work that intends to change transient canvas recovery timing must update the packet-local `transientRecoveryDelayMs` path explicitly instead of assuming the public idle-budget property drives both behaviors.
- Direct geometry commits now intentionally preserve explicit custom heights below the rendered minimum while interactive resize still clamps at the handle and `resize_node()` boundary; future packets should keep that distinction intact when touching graph-size contracts.

## Ready for Integration

- Yes: the substantive packet commit remains `964b8129cb1e94ada19bf3437a37eb5d2b4f47ba`, the wrap-up now matches the execution lifecycle template, and the required packet verification and review-gate commands both pass in the assigned worktree.
