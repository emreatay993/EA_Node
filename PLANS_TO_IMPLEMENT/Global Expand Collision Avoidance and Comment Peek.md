# Global Expand Collision Avoidance and Comment Peek

## Summary
- Add a persistent app-wide graphics behavior that runs collision avoidance when a collapsed item is expanded into occupied space. The expanded item stays fixed, nearby eligible objects move, the result remains after re-collapse, and the entire expand-plus-move action is one undo step.
- Ship a companion `Peek Inside` action for collapsed comment backdrops as a temporary, isolated, fully editable view of the comment's direct current members, with explicit exit control plus click-away dismissal.

## Key Changes
- Extend app preferences and Graphics Settings with a new expand collision-avoidance feature set: enabled toggle, strategy, animation toggle, and advanced controls for participation scope, gap preset, and reach mode or preset.
- Add an expand-time collision solver in the graph-scene mutation path that computes post-expand occupied bounds, translates eligible nearby objects, and commits the expand plus movement in one grouped history action.
- Add a comment-only peek mode with new canvas entrypoints, transient scene state, membership-filtered payload projection, and focused regression coverage.

## Public Interface Changes
- New persistent graphics settings under `graphics.interaction.expand_collision_avoidance`:
  - `enabled`
  - `strategy`
  - `scope`
  - `radius_mode`
  - `local_radius_preset`
  - `gap_preset`
  - `animate`
- New Graphics Settings controls for those values, with a basic section and an optional advanced section.
- New comment-node context-menu action: `Peek Inside`.

## Execution Tasks

### T01 Preferences and Graphics Settings Pipeline
- Goal: Add the new persistent preference schema, normalization, defaulting, runtime application path, and Graphics Settings controls without changing collapse behavior yet.
- Preconditions: `none`
- Conservative write scope: `ea_node_editor/settings.py`, `ea_node_editor/app_preferences.py`, `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`, `ea_node_editor/ui/shell/presenters/workspace_presenter.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui/shell/window_state/run_and_style_state.py`, `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`, `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`, `tests/test_graphics_settings_preferences.py`, `tests/test_graphics_settings_dialog.py`, `tests/test_shell_theme.py`, `tests/graph_track_b/qml_preference_bindings.py`
- Deliverables: normalized defaults for new users and upgraders, live host/runtime application path, Graphics Settings UI with basic and advanced controls, and regression coverage for settings round-trip plus runtime projection.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py tests/test_shell_theme.py tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`
- Non-goals: no expand collision solver, no geometry translation, no comment peek mode, no comment context-menu changes.
- Packetization notes: converts directly to `P01`; later tasks may depend on the preference surface but should not reopen the dialog or normalization rules unless the packet contract explicitly says so.

### T02 Expand Collision Avoidance Solver
- Goal: Add the expand-time collision solver and grouped mutation/history wiring for collapsed item expansion, including comment-backdrop occupied bounds and configurable solver behavior.
- Preconditions: `T01`
- Conservative write scope: `ea_node_editor/ui_qml/graph_scene/context.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation/collision_avoidance_ops.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `ea_node_editor/graph/comment_backdrop_geometry.py`, `ea_node_editor/graph/transform_layout_ops.py`, `ea_node_editor/graph/mutation_service.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_comment_backdrop_membership.py`, `tests/test_comment_backdrop_collapse.py`, `tests/test_graph_surface_input_contract.py`
- Deliverables: expand-only collision solver, one-step undo grouping, local or unbounded propagation, fixed gap presets, animation-ready state exposure, and regression anchors for mutation and backdrop geometry behavior.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_comment_backdrop_membership.py tests/test_comment_backdrop_collapse.py tests/test_graph_surface_input_contract.py --ignore=venv -q`
- Non-goals: no comment peek mode, no new lock or pin behavior, no restore-on-collapse behavior, no batch expand orchestration, no future stylus model implementation beyond keeping the solver adapter-friendly.
- Packetization notes: converts directly to `P02`; this packet owns any inherited regression anchors it must revise from `T01` or existing graph-scene bridge tests.

### T03 Comment Peek Mode and Canvas Entry Points
- Goal: Add the collapsed-comment `Peek Inside` action, transient comment-peek scene state, membership-filtered payload projection, and fully editable focused view behavior.
- Preconditions: `T01`, `T02`
- Conservative write scope: `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`, `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`, `ea_node_editor/ui_qml/graph_scene/context.py`, `ea_node_editor/ui_qml/graph_scene/state_support.py`, `ea_node_editor/ui_qml/graph_scene_scope_selection.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `tests/main_window_shell/bridge_contracts_graph_canvas.py`, `tests/main_window_shell/comment_backdrop_workflows.py`, `tests/main_window_shell/passive_style_context_menus.py`, `tests/test_main_window_shell.py`, `tests/graph_surface_pointer_regression.py`
- Deliverables: comment-only context action, new transient peek state, direct-member-only projection contract, exit affordances, editable peek mode, and focused shell/QML regressions.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/comment_backdrop_workflows.py tests/main_window_shell/passive_style_context_menus.py tests/test_main_window_shell.py tests/graph_surface_pointer_regression.py --ignore=venv -q`
- Non-goals: no reuse of subnode `scope_path` for comment peek, no recursive reveal of nested subnode internals, no new docs or QA-matrix closeout packet.
- Packetization notes: converts directly to `P03`; this packet is the final implementation wave and should absorb any earlier regression anchors it must revise for the new transient peek mode.

## Work Packet Conversion Map
1. `P00 Bootstrap`: create the packet manifest, status ledger, packet specs, prompt files, `.gitignore` allowlist entries, and `docs/specs/INDEX.md` registration while treating this plan file as the review baseline.
2. `P01 Preferences and Graphics Settings Pipeline`: derived primarily from `T01`.
3. `P02 Expand Collision Avoidance Solver`: derived primarily from `T02`.
4. `P03 Comment Peek Mode and Canvas Entry Points`: derived primarily from `T03`.

## Test Plan
- Preferences and dialog regression: `tests/test_graphics_settings_preferences.py`, `tests/test_graphics_settings_dialog.py`, `tests/test_shell_theme.py`, `tests/graph_track_b/qml_preference_bindings.py`
- Expand solver and history regression: `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_comment_backdrop_membership.py`, `tests/test_comment_backdrop_collapse.py`, `tests/test_graph_surface_input_contract.py`
- Comment peek and canvas regression: `tests/main_window_shell/bridge_contracts_graph_canvas.py`, `tests/main_window_shell/comment_backdrop_workflows.py`, `tests/main_window_shell/passive_style_context_menus.py`, `tests/test_main_window_shell.py`, `tests/graph_surface_pointer_regression.py`
- Manual validation after implementation: confirm expansion animates by default, the Graphics Settings toggles live-update the active canvas, and `Peek Inside` exits cleanly by button and by click-away.

## Assumptions
- New users and existing users with missing settings both adopt the new default behavior: collision avoidance enabled, nearest strategy, animation on, `all_movable`, local reach, medium radius preset, and normal gap preset.
- `Peek Inside` is comment-backdrop-only, shows direct current members only, stays fully editable, and does not reuse the subnode scope-path architecture.
- There is no existing lock, pin, or frozen-object concept for node-backed canvas items in this repo, so v1 has no movement exemptions.
- Future stylus content should be treated as rigidly translatable by adapter, but stylus model authoring itself is out of scope for this packet set.
