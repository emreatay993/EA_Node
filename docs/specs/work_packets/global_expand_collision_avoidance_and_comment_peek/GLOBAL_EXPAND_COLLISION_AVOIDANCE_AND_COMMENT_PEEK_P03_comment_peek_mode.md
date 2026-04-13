# GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK P03: Comment Peek Mode

## Packet Metadata

- Packet: `P03`
- Title: `Comment Peek Mode`
- Owning Source Subsystem Packet: [Graph Canvas Packet](../ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md)
- Owning Regression Packet: [Main Window Shell Test Packet](../ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md)
- Inherited Secondary Subsystem Docs: [Graph Scene Packet](../ui_context_scalability_refactor/GRAPH_SCENE_PACKET.md)
- Inherited Secondary Regression Docs: [Graph Surface Test Packet](../ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md), [Track B Test Packet](../ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md)
- Execution Dependencies: `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P02_expand_collision_avoidance.md`

## Objective

- Add the collapsed-comment `Peek Inside` action, new transient comment-peek state, and direct-member-only editable focused view while preserving the existing subnode scope-path architecture and the collision-avoidance behavior delivered by `P02`.

## Preconditions

- `P02` is complete and the packet-owned graph-scene mutation behavior is stable.
- The implementation base is current `main`.

## Execution Dependencies

- `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P02_expand_collision_avoidance.md`

## Target Subsystems

- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/main_window_shell/passive_style_context_menus.py`
- `tests/test_main_window_shell.py`
- `tests/graph_surface_pointer_regression.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/main_window_shell/passive_style_context_menus.py`
- `tests/test_main_window_shell.py`
- `tests/graph_surface_pointer_regression.py`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/P03_comment_peek_mode_WRAPUP.md`

## Source Public Entry Points

- `GraphCanvasContextMenus.nodeContextPopup`
- graph-canvas command bridge request path for node context actions
- graph-scene read and payload projection surfaces
- transient graph-scene state exposed through the bridge

## Regression Public Entry Points

- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/main_window_shell/passive_style_context_menus.py`
- `tests/test_main_window_shell.py`
- `tests/graph_surface_pointer_regression.py`

## State Owner

- Comment peek is transient scene or UI state owned by the active graph-scene bridge layer. It must not be persisted into project files or reused as `scope_path`.

## Allowed Dependencies

- [PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md](../../../../PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md)
- [GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md](./GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md)
- [Graph Canvas Packet](../ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md)
- [Graph Scene Packet](../ui_context_scalability_refactor/GRAPH_SCENE_PACKET.md)
- [Main Window Shell Test Packet](../ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md)
- [Graph Surface Test Packet](../ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md)
- [Track B Test Packet](../ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md)

## Required Invariants

- `Peek Inside` is available only on collapsed comment backdrops.
- Comment peek does not reuse subnode `scope_path` or breadcrumb navigation.
- Comment peek shows the backdrop plus direct current members only; it does not recursively reveal nested subnode internals.
- The peek view remains fully editable.
- The user can exit by explicit control and by clicking away.
- Existing expand collision-avoidance behavior remains intact.

## Forbidden Shortcuts

- Do not overload comment peek onto the existing `open_subnode_scope` path.
- Do not widen the mode into generic “show anything inside bounds” geometry.
- Do not persist comment peek state into app preferences or `.sfe` documents.
- Do not reopen `P01` settings work or `P02` solver behavior except where inherited regression anchors genuinely need updates.

## Required Tests

- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/main_window_shell/passive_style_context_menus.py`
- `tests/test_main_window_shell.py`
- `tests/graph_surface_pointer_regression.py`

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/comment_backdrop_workflows.py tests/main_window_shell/passive_style_context_menus.py tests/test_main_window_shell.py tests/graph_surface_pointer_regression.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/comment_backdrop_workflows.py --ignore=venv -q
```

## Expected Artifacts

- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/main_window_shell/passive_style_context_menus.py`
- `tests/test_main_window_shell.py`
- `tests/graph_surface_pointer_regression.py`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/P03_comment_peek_mode_WRAPUP.md`

## Acceptance Criteria

- Collapsed comment backdrops expose a `Peek Inside` action through the node context menu.
- Activating `Peek Inside` opens a temporary focused view that shows only the comment backdrop and its direct current members.
- The peek view remains editable and exits by explicit control and by click-away.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- This is the final implementation packet in the set.
- If later closeout work is needed, publish it as a separate packet set rather than widening `P03`.
