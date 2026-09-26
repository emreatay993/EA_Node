# Swimlane Pools And Lanes

## Purpose
Use this for swimlane pools and their role lanes: the two node types, the stacked-lane rule (lanes resize together,
nodes stay in their lanes), lane drags and reorder, lane commands, the lane-aware Tidy, the pool/lane surface and
title band, the lane context menu, persistence of pools, and the `swimlane.*` automation ops.

## Start Here
- `ea_node_editor/nodes/builtins/passive_annotation.py`: `passive.annotation.swimlane_pool` (collapsible; `title`,
  `orientation` horizontal|vertical) and `passive.annotation.swimlane_lane` (not collapsible, no ports; `title` is
  the role name, `orientation` follows its pool). Both are in the `group_backdrop` surface family, so the Group rules
  apply as they are: `compute_group_backdrop_membership` (a node in a lane belongs to the lane, the smallest Group
  around it), drag carry of contents, collapse/Peek of a pool, backdrop render layering, title sync on load.
  `PASSIVE_ANNOTATION_BACKDROP_TYPE_IDS` lets `ea_node_editor/graph/hierarchy.py` keep a collapsed pool's (and its
  hidden lanes') stored member lists on load.
- `ea_node_editor/graph/swimlane_layout.py`: the pure rule, in a horizontal frame (a vertical pool is transposed):
  `restack_swimlane_pool` (lanes follow each other from the pool start and span its length; an item crossing a
  lane's start side is nudged in, an end side grows the lane or every lane; items just placed are nudged fully
  inside when they fit; a lane moved along the flow comes back in line with its items),
  `resolve_swimlane_lane_resize` / `resolve_swimlane_pool_resize` (edge-aware, clamped to contents and minimums),
  `absorb_removed_swimlane_lane`, `swimlane_lane_index_at`, `order_swimlane_lanes`, `new_swimlane_pool_frames`, and
  `swimlane_pool_lane_ids_from_records` (a pool's lanes from stored frames: copy and delete take them along through
  `ea_node_editor/graph/transform_fragment_ops.py`).
- `ea_node_editor/ui_qml/graph_scene_mutation/swimlane_ops.py`: `capture_swimlanes` before a mutation and
  `settle_swimlanes` after it (same undo step) restack every expanded pool of the open scope. A node keeps the lane it
  had unless it was moved without that lane or is new; then the lane its centre lands in takes it. A lane moved on its
  own joins the pool of its orientation its centre lands in, else returns to its old slot; a new lane outside every
  pool gets a pool. Commands: `create_swimlane_pool`, `initialize_swimlane_pool` (a Library-dropped pool gets three
  lanes), `add_swimlane_lane` / `insert_swimlane_lane`, `remove_swimlane_lane` (the lane before it, else after it,
  takes its band and nodes), `move_swimlane_lane`, `assign_nodes_to_swimlane_lane`, `resize_swimlane_frame`,
  `set_swimlane_pool_orientation` (rows become columns; every node keeps its lane and flow position), and the
  read-only `describe_swimlane_pools`.
- Settle hooks (callers own their undo step and publish a full rebuild when settle changed anything):
  `move_node`, `move_nodes_by_delta` and `set_node_geometry` in
  `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py` (lanes and expanded pools resize
  through `resize_swimlane_frame`); `create_node_from_type`, `remove_node_with_policy`, `set_node_collapsed`,
  `set_node_settings_group_expanded` and pool `orientation` property edits in
  `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`; paste/duplicate, align/distribute and
  Delete Selection in `ea_node_editor/ui_qml/graph_scene_mutation_history.py`; Group wrap in
  `ea_node_editor/ui_qml/graph_scene_mutation/group_backdrop_ops.py`; Tidy in
  `ea_node_editor/ui_qml/graph_scene_mutation/tidy_layout_ops.py`.
- Lane-aware Tidy: `_TidyLayoutRun._resolve_swimlane_pool` in `ea_node_editor/graph/transform_tidy_layout.py`
  (`TidyItem.swimlane_pool` / `swimlane_lane`): layer columns along the pool's flow shared by every lane, one row per
  lane (two steps of a lane in one layer stack across it), lanes sized to what they hold and restacked. The scene
  Tidy pulls a lane's pool in when a lane is selected.
- The settle pass measures after mutating: `scene_layout_bounds` in
  `ea_node_editor/ui_qml/graph_scene_mutation/group_scope.py` measures a node afresh when its cached payload no longer
  matches it (moved, collapsed/expanded, backdrop resized) or when it is in `stale_ids`.
- QML: `ea_node_editor/ui_qml/components/graph/passive/GraphSwimlaneSurface.qml` (mapped per variant in
  `ea_node_editor/ui_qml/surface_contracts.py`; metrics in `GraphNodeSurfaceMetricContract.json` / `.js`):
  pool sheet (theme `panel_alt_bg`), title band, lane role band and dividers, hidden in the input-overlay copy.
  `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml` turns an expanded horizontal pool's or lane's
  title up its band (`swimlaneTitleRotated`; the shared title editor turns with it and
  `surface_controls/SurfaceControlGeometry.js` maps rotated hit rects); a collapsed pool's pill keeps an upright title
  and shows the pool glyph (`layout-dashboard`, `groupTitleIconSource`) where a Group shows `comment`. `GraphNodeHost.qml` stacks backdrops by
  `backdrop_depth` (lanes above their pool in both backdrop layers, even with the pool selected).
- Context menu (node-local route): `_swimlaneActions` / `_handleSwimlaneAction` in
  `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml` (pool: Add Lane, Tidy Lanes; lane:
  Insert Lane Above/Below or Left/Right, Move Lane Up/Down or Left/Right, Tidy Lanes, Remove Lane) call the slots in
  `ea_node_editor/ui_qml/graph_canvas_command/scene_mutation_ops.py`; the pre-open height estimate is in
  `GraphCanvasInteractionState.qml`.
- Automation: `swimlane.create_pool`, `swimlane.add_lane`, `swimlane.remove_lane`, `swimlane.move_lane`,
  `swimlane.assign`, `swimlane.describe` in `ea_node_editor/automation/ops/structure.py` and
  `ea_node_editor/ui/shell/automation/handlers/structure.py`; `layout.tidy` takes one pool id. MCP guidance: guide
  step 6 and the node-types resource in `ea_node_editor/automation/guidance.py`.

## Do Not Start Here
- `GraphGroupBackdropSurface.qml` draws only the plain Group; swimlanes have their own surface.
- The make-room cascade (`collision_avoidance_ops.py`) knows nothing of lanes; the settle pass after it restacks.

## Common Changes
- Band sizes, padding, minimums and defaults: constants at the top of `ea_node_editor/graph/swimlane_layout.py` (the
  metric contract variants and `ea_node_editor/automation/ops/structure.py` restate some; `tests/automation/test_catalog.py`
  keeps the automation copies in sync).
- New lane command: add the scene op in `swimlane_ops.py` (one `grouped_history_action`, then `settle_swimlanes`),
  bind it on `GraphSceneMutationHistory`, expose it on `ea_node_editor/ui_qml/graph_scene/command_bridge.py` and
  `ea_node_editor/ui_qml/graph_scene/state_support.py`, add a canvas slot and a menu row.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_swimlane_layout.py tests/test_swimlane_scene_ops.py tests/test_swimlane_tidy_layout.py tests/test_swimlane_persistence.py tests/automation/test_handlers_swimlanes.py -q -n auto
.\venv\Scripts\python.exe -m pytest tests/test_swimlane_shell.py -q -n 0
.\venv\Scripts\python.exe -m pytest tests/test_group_scope.py tests/test_group_backdrop_identity_membership.py tests/test_graph_scene_tidy_layout.py tests/test_transform_tidy_layout.py -q -n auto
```

## Breadcrumbs
- [Group Backdrops, Peek, And Membership](group_backdrops_peek_membership.md) for the membership rules lanes reuse.
- [Graph Actions And Context Menus](graph_actions_and_context_menus.md) for Tidy.
- [Automation API And MCP Server](automation_api_mcp.md) for the op catalog and guidance.
- [Serialization, Migration, And Legacy Rejection](serialization_migration_legacy_rejection.md) for the `.cxproj` path.

## Update Triggers
Update when the stacked-lane rule, lane assignment, lane commands, the settle hooks, the lane-aware Tidy, the pool or
lane surface, title band or menu rows, or the `swimlane.*` ops change.
