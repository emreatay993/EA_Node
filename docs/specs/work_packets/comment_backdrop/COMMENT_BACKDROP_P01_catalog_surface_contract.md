# COMMENT_BACKDROP P01: Catalog + Surface Contract

## Objective
- Add the dedicated zero-port comment-backdrop node type, the `comment_backdrop` surface family contract, and the basic host-path surface and metric defaults that later packets will move onto a dedicated backdrop layer.

## Preconditions
- `P00` is marked `PASS` in [COMMENT_BACKDROP_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md).
- No later `COMMENT_BACKDROP` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/nodes/builtins/passive_annotation.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `tests/test_comment_backdrop_contracts.py`
- `tests/test_registry_filters.py`

## Conservative Write Scope
- `ea_node_editor/nodes/builtins/passive_annotation.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `tests/test_comment_backdrop_contracts.py`
- `tests/test_registry_filters.py`
- `docs/specs/work_packets/comment_backdrop/P01_catalog_surface_contract_WRAPUP.md`

## Required Behavior
- Register `passive.annotation.comment_backdrop` under the existing `Annotation` category as a dedicated backdrop primitive rather than another note-style annotation card.
- Lock the new type to:
  - `runtime_behavior="passive"`
  - `surface_family="comment_backdrop"`
  - `surface_variant="comment_backdrop"`
  - zero ports
  - `collapsible=True`
  - properties `title` and `body`, with the long-form body using the existing multiline editor metadata path
- Add a dedicated surface component and metric contract for the backdrop so it renders coherently through the current host path before the later layer split lands.
- Keep this packet additive and contract-first: existing annotation cards stay connectable, note-style, and visually unchanged.
- Ensure the new backdrop type round-trips through the existing graph serializer and registry filters without introducing persisted member lists or dedicated backdrop-only document storage.

## Non-Goals
- No dedicated backdrop payload model or under-edge canvas layer yet. `P02` owns the layer split.
- No geometry ownership, wrap-selection, nested backdrop behavior, or descendant motion yet. `P03` and `P04` own those semantics.
- No shell action, shortcut, or inline body editing workflow yet. `P06` owns those user-facing affordances.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_contracts.py --ignore=venv -q`
2. `./venv/Scripts/python.exe -m pytest tests/test_registry_filters.py --ignore=venv -k "annotation" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_contracts.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/comment_backdrop/P01_catalog_surface_contract_WRAPUP.md`

## Acceptance Criteria
- The registry exposes `passive.annotation.comment_backdrop` as a dedicated collapsible zero-port backdrop type under `Annotation`.
- The backdrop surface family has explicit QML and metric support without changing existing note-style annotation cards.
- Serializer and registry coverage confirm the new backdrop node stays on the normal graph document path and does not persist membership state.
- The backdrop can render through the existing host path as an intermediate foundation for the later layer split.

## Handoff Notes
- `P02` must move the backdrop off the regular node layer without renaming the new type, surface family, or surface variant.
- Record the default width, height, and visual affordances in the wrap-up so later packets reuse the same contract instead of opening a second size authority.
