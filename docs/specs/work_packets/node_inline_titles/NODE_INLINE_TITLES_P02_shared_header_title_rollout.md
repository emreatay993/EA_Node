# NODE_INLINE_TITLES P02: Shared Header Title Rollout

## Objective
- Expand the existing shared header title editor from flowchart-only usage to the non-scoped graph node families without introducing per-surface title-edit code paths.

## Preconditions
- `P01` is marked `PASS` in [NODE_INLINE_TITLES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_STATUS.md).
- No later `NODE_INLINE_TITLES` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostHitTesting.js`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostHitTesting.js`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`
- `docs/specs/work_packets/node_inline_titles/P02_shared_header_title_rollout_WRAPUP.md`

## Required Behavior
- Replace the flowchart-only title-edit gate with a generic shared-header capability for nodes that are not scope-capable (`canEnterScope == false`) and are not yet part of the scoped/collapsed rollout reserved for `P03`.
- Reuse the current shared header editor, object names, and `inlinePropertyCommitted(nodeId, "title", value)` signal path. Do not add a title-specific canvas bridge API or any surface-local title editor.
- Preserve current flowchart behavior while adding the same double-click-to-edit, Enter/focus-loss commit, Escape cancel, and pointer-isolation behavior to at least the standard executable and passive non-flowchart surfaces.
- Keep single-click title selection behavior intact and preserve current non-title body double-click behavior for nodes that are not yet in the scoped rollout.
- Add focused host/canvas regressions that prove non-scoped standard and passive nodes now use the shared header title editor without regressing pointer routing.

## Non-Goals
- No subnode scope-entry changes in this packet.
- No collapsed-node title editing in this packet.
- No mutation-layer authority changes; `P01` already owns that seam.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "title" -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "title" -q`

## Expected Artifacts
- `docs/specs/work_packets/node_inline_titles/P02_shared_header_title_rollout_WRAPUP.md`

## Acceptance Criteria
- Non-scoped standard and passive node families can enter the shared inline title editor from the header/title gesture path.
- The rollout does not introduce a second title-edit API or surface-local title editor.
- Existing flowchart inline-title behavior remains intact.
- Focused host/canvas regressions pass.

## Handoff Notes
- Record any renamed internal QML property names if the flowchart-specific naming is generalized, but keep test-facing object names stable unless the packet owns an explicit test update.
- Leave scope-capable/collapsed behavior untouched for `P03`; document any intentional temporary exclusions clearly in the wrap-up.
