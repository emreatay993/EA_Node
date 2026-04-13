# Global Expand Collision Avoidance and Comment Peek

## Summary
- Add a persistent app-wide Graphics preference that runs collision avoidance only when a collapsed item is expanded. It applies to any collapsed scene item that expands in place now, and the solver should be extensible to future rigid stylus/freehand items.
- Default behavior: enabled for both new users and upgraders when the setting is absent; the expanded item stays fixed; nearby eligible objects move; the whole expand-plus-move operation is one undo step; re-collapsing does not restore prior auto-moved positions; edges are ignored as blockers.
- Ship `Peek Inside` in the same milestone as a comment-only, temporary isolated view for collapsed comment backdrops.

## Interfaces
- Extend `graphics.interaction` in [settings.py](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/settings.py) with an `expand_collision_avoidance` object:
  - `enabled: bool = true`
  - `strategy: "nearest" | "radial" | "sweep" = "nearest"`
  - `scope: "all_movable" | "structured_only" | "nodes_only" = "all_movable"`
  - `radius_mode: "local" | "unbounded" = "local"`
  - `local_radius_preset: "near" | "medium" | "far" = "medium"`
  - `gap_preset: "tight" | "normal" | "loose" = "normal"`
  - `animate: bool = true`
- Do not persist the dialog’s “Show advanced controls” expander state.
- Add transient scene/view state `comment_peek_backdrop_id: str | None` plus a command-bridge action `request_peek_inside_comment_node(node_id)`; this is UI state only, not project data.

## Implementation Changes
- Preferences and UI:
  - Normalize and persist the new settings through the existing app-preferences pipeline; missing values adopt the new defaults with no prompt.
  - Add a basic Graphics Settings section with `Enable expansion collision avoidance`, `Push strategy`, and `Animate moved objects`.
  - Add an advanced expander with `Gap`, `Participation scope`, `Reach`, and `Local reach size`.
  - Preset mapping:
    - Gap: `Tight=16`, `Normal=32`, `Loose=64` scene units.
    - Local reach: inflate the expanded footprint by `Near=1x`, `Medium=2x`, `Far=4x` of the expanded footprint’s max dimension.
- Expand auto-push:
  - In [selection_and_scope_ops.py](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py), intercept only `collapsed -> expanded` when the feature is enabled.
  - Compute a non-mutating post-expand footprint before commit. For comment backdrops, the fixed footprint is the backdrop plus its current direct members; for subnodes and other nodes, use the post-expand projected visible bounds. Internal contents keep their relative layout and are never rearranged.
  - Reuse the existing grouped layout-update path (`set_node_position` / `_apply_layout_updates`) so collapse-state change and all translations land in one history group, followed by one rebuild.
  - Solver rules:
    - Eligible participants come from the selected scope preset.
    - Current implementation should move all existing movable node-backed items; the solver contract must also support future rigid stylus/freehand participants by adapter.
    - `nearest`: minimum separating translation against current occupied bounds.
    - `radial`: push away from expanded-item center.
    - `sweep`: push along the dominant overlap axis.
    - `local`: only items intersecting the inflated influence region may move.
    - `unbounded`: downstream collisions may keep enrolling until stable.
    - Resolve until the eligible set is clash-free against the fixed expanded footprint and itself. Items outside the eligible set do not move.
- Comment `Peek Inside`:
  - Add a collapsed-comment-only context action in [GraphCanvasContextMenus.qml](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml).
  - Route click-away and `Escape` dismissal through [GraphCanvasInputLayers.qml](C:/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml).
  - Implement peek as a dedicated membership-filtered scene mode, not `scope_path`.
  - Show the comment backdrop plus its current direct members in the current canvas scope; do not recursively open nested subnode contents. Show only edges whose endpoints are still visible.
  - Peek mode is fully editable.
  - Exit affordances: visible `Back/Exit Peek` control plus click-empty-canvas dismissal.
  - On exit, return to the normal canvas view with the backdrop reselected.

## Test Plan
- Preference tests: missing keys normalize to enabled defaults; round-trip persistence; legacy preference docs load without prompt/version breakage.
- Solver tests: nearest/radial/sweep produce deterministic non-overlapping results; `local` vs `unbounded`; gap presets; comment expansion keeps internal layout fixed; re-collapse does not restore positions.
- Mutation/history tests: expand plus auto-move records one undo action; undo/redo restores both collapse state and moved positions; disabled setting preserves current behavior.
- Peek tests: action appears only on collapsed comment backdrops; filtered view shows direct members only; edits inside peek persist; exit works by button and empty-canvas click; normal subnode scope navigation is unchanged.

## Assumptions
- Current repo has no object-level lock/pin concept, so v1 has no movement exemptions.
- Current collapse UX is single-node oriented; batch expand/collapse is not part of this milestone.
- Default user-facing behavior is `enabled + nearest + animation on`; advanced defaults are `all_movable + local/medium + normal gap`.
