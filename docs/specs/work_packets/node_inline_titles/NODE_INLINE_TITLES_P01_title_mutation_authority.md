# NODE_INLINE_TITLES P01: Title Mutation Authority

## Objective
- Converge inline title edits onto the existing graph rename authority so non-flowchart nodes can participate in inline title editing without introducing a second mutation workflow.

## Preconditions
- `P00` is marked `PASS` in [NODE_INLINE_TITLES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_STATUS.md).
- No later `NODE_INLINE_TITLES` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/test_inspector_reflection.py`
- `tests/graph_track_b/scene_and_model.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/test_inspector_reflection.py`
- `tests/graph_track_b/scene_and_model.py`
- `docs/specs/work_packets/node_inline_titles/P01_title_mutation_authority_WRAPUP.md`

## Required Behavior
- Route `set_node_property(node_id, "title", value)` through the same normalization, empty-value rejection, and surface-title synchronization rules that back `set_node_title(...)`.
- Make `set_node_properties(node_id, values)` safe when `values` includes `"title"` for node types that do not declare a `title` property in the registry, including standard executable nodes and subnode shells.
- Keep property-backed passive families (`flowchart`, `planning`, `annotation`) synchronized on both `node.title` and `properties["title"]`, while standard/media/subnode nodes continue to treat `node.title` as the canonical stored title.
- Preserve single-title rename semantics: direct title-only mutations should continue to use the rename authority and its existing history meaning; bulk property updates that happen to include `title` may keep the batch-style property history contract as long as they still reuse the same normalization/sync helper internally.
- Avoid a second canvas/QML title API in this packet. The mutation-layer authority is the seam; QML still calls the existing property commit path for now.

## Non-Goals
- No QML gesture changes in this packet.
- No shared-header/editor rollout in this packet.
- No subnode `OPEN` badge behavior changes in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_inspector_reflection.py --ignore=venv -k "title" -q`
2. `./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -k "title or titles_synced" -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_inspector_reflection.py --ignore=venv -k "title" -q`

## Expected Artifacts
- `docs/specs/work_packets/node_inline_titles/P01_title_mutation_authority_WRAPUP.md`

## Acceptance Criteria
- Title-only mutations no longer depend on a declared `title` property and do not raise registry/property-key errors on standard nodes or subnode shells.
- Flowchart/planning/annotation title mutations remain synchronized between `node.title` and `properties["title"]`.
- The packet does not add a second public title-commit API to the canvas/QML bridge surface.
- Focused mutation-layer regressions pass.

## Handoff Notes
- Record the exact internal helper/authority seam in the wrap-up so later QML packets target it rather than reimplementing title normalization in the UI layer.
- If bulk `set_node_properties(...)` retains `ACTION_EDIT_PROPERTY` while reusing the title helper, note that explicitly so later packets do not assume every title-bearing mutation becomes `ACTION_RENAME_NODE`.
