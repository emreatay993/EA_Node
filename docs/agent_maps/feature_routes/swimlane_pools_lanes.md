# Swimlane Pools And Lanes

## Purpose
Use this for swimlanes: the lane (the Library's Swimlane) and the pool that forms around two or more lanes, the
stacked-lane rule (lanes resize together, nodes stay in their lanes), standalone lanes, pools forming and dissolving,
lane drags (a reorder inside the pool), lane commands and "+" buttons, lane colours, the live previews (resize, lane
reorder, the lane a drag drops into), the lane-aware Tidy, the pool/lane surface and title band, the lane context menu,
the Inspector's Lanes section, persistence, and the `swimlane.*` automation ops.

## Start Here
- `ea_node_editor/nodes/builtins/passive_annotation.py`: `passive.annotation.swimlane_lane` (display name
  "Swimlane"; not collapsible, no ports; `title` is the role name, `orientation` horizontal|vertical, `color` "#rrggbb"
  or "" for the theme's) and `passive.annotation.swimlane_pool` (collapsible; `title`, `orientation`). Both are in the
  `group_backdrop` surface family, so the Group rules apply as they are: `compute_group_backdrop_membership` (a node
  in a lane belongs to the lane, the smallest Group around it), drag carry of contents, collapse/Peek of a pool,
  backdrop render layering, title sync on load. `PASSIVE_ANNOTATION_BACKDROP_TYPE_IDS` lets
  `ea_node_editor/graph/hierarchy.py` keep a collapsed pool's (and its hidden lanes') stored member lists on load.
  `LIBRARY_HIDDEN_NODE_TYPE_IDS` keeps the pool out of the Library (`build_registry_library_items` in
  `ea_node_editor/ui/shell/library_projection.py`): the Library offers the lane, and a pool forms from lanes.
- `ea_node_editor/graph/swimlane_layout.py`: the pure rule, in a horizontal frame (a vertical pool is transposed):
  `restack_swimlane_pool` (lanes follow each other from the pool start and span its length; an item crossing a
  lane's start side is nudged in, an end side grows the lane or every lane; items just placed are nudged fully
  inside when they fit; a lane moved along the flow comes back in line with its items; with no lanes it lays out a
  lane-less pool, which is also how a standalone lane is laid out), `resolve_swimlane_lane_resize` /
  `resolve_swimlane_pool_resize` (edge-aware, clamped to contents and minimums), `absorb_removed_swimlane_lane`,
  `swimlane_lane_index_at`, `order_swimlane_lanes`, `new_swimlane_pool_frames`, and
  `swimlane_pool_lane_ids_from_records` (a pool's lanes from stored frames: copy and delete take them along through
  `ea_node_editor/graph/transform_fragment_ops.py`).
- `ea_node_editor/ui_qml/graph_scene_mutation/swimlane_ops.py`: `capture_swimlanes` before a mutation and
  `settle_swimlanes` after it (same undo step) restack every expanded pool and standalone lane of the open scope
  (`SwimlanePoolSnapshot.standalone`: a lane in no pool holds its items itself, like a lane-less pool). A node keeps
  the lane it had unless it was moved without that lane or is new; then the lane its centre lands in takes it. A lane
  moved on its own joins the pool of its orientation its centre lands in, else returns to its old slot; a new or
  standalone lane joins the pool its centre lands in, forms a pool with a standalone lane it lands on
  (`_form_pools_for_lane_drops`), else stays on its own. Commands: `create_swimlane_lane` (one lane),
  `create_swimlane_pool`, `initialize_swimlane_pool` (a pool created by automation gets its lanes), `add_swimlane_lane`
  / `insert_swimlane_lane` (next to a standalone lane it forms a pool, `_form_pool_around_lane`: the title band goes
  outside, so the lane does not move), `remove_swimlane_lane` (the lane before it, else after it, takes its band and
  nodes; a pool left with one lane dissolves, `dissolved_swimlane_pool_ids`, which every removal path adds to what it
  removes), `move_swimlane_lane` / `reorder_swimlane_lane`, `assign_nodes_to_swimlane_lane`, `resize_swimlane_frame`,
  `set_swimlane_orientation` (a lane turns its pool; a standalone lane turns about its corner,
  `_transpose_standalone_lane`), and the read-only `describe_swimlane_pools` / `describe_standalone_swimlane_lanes`.
- Live previews, read-only and computed by the commit's own rules: `preview_swimlane_resize` (the frames of a lane or
  pool resize and the nodes it moves), `preview_swimlane_lane_drag` (a lane's offset kept on its pool's stack axis and
  inside the pool, the slot it would take — a neighbour is passed once the lane's leading edge crosses its centre —
  and the lanes it passes), `preview_swimlane_drop` (a dry-run settle at the dragged offset: the lanes the drop
  grows or pushes and the `targets` it lands in). `_preview_state` caches the snapshot and scope per gesture
  (`session`) and scene revision.
- Settle hooks (callers own their undo step and publish a full rebuild when settle changed anything):
  `move_node`, `move_nodes_by_delta` and `set_node_geometry` in
  `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py` (lanes and expanded pools resize
  through `resize_swimlane_frame`); `create_node_from_type`, `remove_node_with_policy`, `set_node_collapsed`,
  `set_node_settings_group_expanded` and pool or lane `orientation` property edits in
  `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`; paste/duplicate, align/distribute and
  Delete Selection (which adds dissolving pools up front) in `ea_node_editor/ui_qml/graph_scene_mutation_history.py`;
  Group wrap in `ea_node_editor/ui_qml/graph_scene_mutation/group_backdrop_ops.py`; Tidy in
  `ea_node_editor/ui_qml/graph_scene_mutation/tidy_layout_ops.py`.
- Lane-aware Tidy: `_TidyLayoutRun._resolve_swimlane_pool` in `ea_node_editor/graph/transform_tidy_layout.py`
  (`TidyItem.swimlane_pool` / `swimlane_lane`): layer columns along the pool's flow shared by every lane, one row per
  lane (two steps of a lane in one layer stack across it), lanes sized to what they hold and restacked. The scene
  Tidy pulls a lane's pool in when a lane is selected, and flags a standalone lane as a pool without lanes
  (`_held_by_swimlane_pool`).
- The settle pass measures after mutating: `scene_layout_bounds` in
  `ea_node_editor/ui_qml/graph_scene_mutation/group_scope.py` measures a node afresh when its cached payload no longer
  matches it (moved, collapsed/expanded, backdrop resized) or when it is in `stale_ids`.
- QML surface: `ea_node_editor/ui_qml/components/graph/passive/GraphSwimlaneSurface.qml` (mapped per variant in
  `ea_node_editor/ui_qml/surface_contracts.py`; metrics in `GraphNodeSurfaceMetricContract.json` / `.js`): pool sheet
  (theme `panel_alt_bg`), title band, lane role band and dividers; a standalone lane (its payload's
  `owner_backdrop_id` is not a pool) draws the sheet and frame itself; a lane colour tints its band and lightly the
  lane; the lane or pool a drag drops into lights up (`swimlaneDropTargetLookup`). The input-overlay copy draws only a
  lane's hover "+" buttons (`embeddedInteractiveRects`, so they never start a lane drag; hidden below zoom 0.45), which
  call `insert_swimlane_lane`. `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml` turns an expanded
  horizontal pool's or lane's title up its band (`swimlaneTitleRotated`; the shared title editor turns with it and
  `surface_controls/SurfaceControlGeometry.js` maps rotated hit rects); a collapsed pool's pill keeps an upright title
  and shows the pool glyph (`layout-dashboard`, `groupTitleIconSource`) where a Group shows `comment`.
  `GraphNodeHost.qml` stacks backdrops by `backdrop_depth` (lanes above their pool in both backdrop layers).
- Live previews on the canvas: `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSwimlanePreview.qml` (the
  canvas's `swimlanePreviewObject`, `swimlaneDropTargetLookup`, `previewSwimlaneResize`, `swimlaneLaneReorderCommit`).
  `GraphCanvasSceneState.qml` calls `beginMove` when a drag freezes its moving set (a lane in a pool drags alone, as a
  reorder, and skips the smart guides), `resolveMove` once per flushed frame (the lane's kept offset, or the drop
  preview when the dragged nodes overlap a lane), and `endMove` in `clearLiveDragOffset`.
  `GraphCanvasNodeDelegate.qml` routes a swimlane `resizePreviewChanged` to `previewSwimlaneResize` and commits a lane
  drag with `reorder_swimlane_lane` instead of a move. Previews write the shared `liveNodeGeometry` map in one
  assignment and never an entry for a node in the live drag set; a scene mutation (the commit) clears it. Canvas slots
  `swimlane_resize_preview`, `swimlane_lane_drag_preview`, `swimlane_drop_preview` and `reorder_swimlane_lane` live in
  `ea_node_editor/ui_qml/graph_canvas_command/scene_mutation_ops.py`.
- Context menu (node-local route): `_swimlaneActions` / `_handleSwimlaneAction` in
  `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml` (pool: Add Lane, Tidy Lanes, Switch to
  Vertical/Horizontal Lanes; lane in a pool: Insert Lane Above/Below or Left/Right, Move Lane Up/Down or Left/Right,
  Tidy Lanes, the orientation switch, Remove Lane; standalone lane: the insert rows, Tidy Lane, the orientation
  switch, Remove Lane) call the slots in `ea_node_editor/ui_qml/graph_canvas_command/scene_mutation_ops.py`; the
  pre-open height estimate is in `GraphCanvasInteractionState.qml`.
- Inspector Lanes section: `ea_node_editor/ui_qml/components/shell/InspectorSwimlaneLanesSection.qml` (rows keyed
  by lane id through `InspectorRowsModel`: colour swatch, role name, move up/down, remove, Add Lane), mounted in
  `InspectorPane.qml` (`isSwimlaneInspector`, `selectedNodeSwimlaneLaneItems`). Rows come from
  `build_selected_node_swimlane_lane_items` in `ea_node_editor/ui/shell/inspector_projection.py`; the actions and
  the lane colour picker are in `ea_node_editor/ui/shell/presenters/inspector_presenter.py` (they call the scene's
  lane commands) behind `ea_node_editor/ui_qml/shell_inspector_bridge.py`. `on_scene_nodes_changed` (wired in
  `ea_node_editor/ui/shell/window.py`) refreshes the section when lanes change while a pool or lane is selected.
  Tooltip keys `inspector.swimlane_lanes.*` are in `ea_node_editor/ui/tooltips/inspector.json`.
- Automation: `swimlane.create_pool` (two or more lanes), `swimlane.create_lane`, `swimlane.add_lane` (a pool and
  index, or `lane_node_id` and `after`), `swimlane.remove_lane` (`dissolved_pool_node_id`), `swimlane.move_lane`,
  `swimlane.assign`, `swimlane.describe` (`pools` and standalone `lanes`) in
  `ea_node_editor/automation/ops/structure.py` and `ea_node_editor/ui/shell/automation/handlers/structure.py`;
  `layout.tidy` takes one pool id. MCP guidance: guide step 6 and the node-types resource in
  `ea_node_editor/automation/guidance.py`.

## Do Not Start Here
- `GraphGroupBackdropSurface.qml` draws only the plain Group; swimlanes have their own surface.
- The make-room cascade (`collision_avoidance_ops.py`) knows nothing of lanes; the settle pass after it restacks.
- Do not give the lanes a lane reorder passes a second live drag offset: the drag model keeps one shared offset
  (`tests/test_graph_canvas_frame_coalescing.py` rejects `liveDragOffsets` in `GraphCanvasSceneState.qml`); they move
  through `liveNodeGeometry` entries.

## Common Changes
- Band sizes, padding, minimums and defaults: constants at the top of `ea_node_editor/graph/swimlane_layout.py` (the
  metric contract variants and `ea_node_editor/automation/ops/structure.py` restate some; `tests/automation/test_catalog.py`
  keeps the automation copies in sync).
- New lane command: add the scene op in `swimlane_ops.py` (one `grouped_history_action`, then `settle_swimlanes`),
  bind it on `GraphSceneMutationHistory`, expose it on `ea_node_editor/ui_qml/graph_scene/command_bridge.py` and
  `ea_node_editor/ui_qml/graph_scene/state_support.py`, add a canvas slot and a menu row (and an Inspector action when
  it edits a lane).
- A new preview: compute it in `swimlane_ops.py` from the commit's rule (read-only), add a canvas slot, and apply it
  in `GraphCanvasSwimlanePreview.qml` through `_applyPreview`.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_swimlane_layout.py tests/test_swimlane_scene_ops.py tests/test_swimlane_tidy_layout.py tests/test_swimlane_persistence.py tests/automation/test_handlers_swimlanes.py -q -n auto
.\venv\Scripts\python.exe -m pytest tests/test_swimlane_shell.py -q -n 0
.\venv\Scripts\python.exe -m pytest tests/test_inspector_projection.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_canvas_frame_coalescing.py -q -n auto
.\venv\Scripts\python.exe -m pytest tests/test_group_scope.py tests/test_group_backdrop_identity_membership.py tests/test_graph_scene_tidy_layout.py tests/test_transform_tidy_layout.py -q -n auto
```

## Breadcrumbs
- [Group Backdrops, Peek, And Membership](group_backdrops_peek_membership.md) for the membership rules lanes reuse.
- [Graph Canvas Input Layers](graph_canvas_input_layers.md) for the drag and resize pipeline the previews hook into.
- [Graph Actions And Context Menus](graph_actions_and_context_menus.md) for Tidy.
- [Automation API And MCP Server](automation_api_mcp.md) for the op catalog and guidance.
- [Serialization, Migration, And Legacy Rejection](serialization_migration_legacy_rejection.md) for the `.cxproj` path.

## Update Triggers
Update when the stacked-lane rule, lane assignment, standalone lanes or pools forming/dissolving, lane commands, the
settle hooks, the live previews, the "+" buttons, lane colours, the lane-aware Tidy, the pool or lane surface, title
band or menu rows, the Inspector Lanes section, or the `swimlane.*` ops change.
