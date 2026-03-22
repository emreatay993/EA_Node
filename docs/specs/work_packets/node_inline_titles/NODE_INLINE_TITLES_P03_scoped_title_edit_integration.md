# NODE_INLINE_TITLES P03: Scoped Title Edit Integration

## Objective
- Preserve subnode scope entry while finishing the inline-title rollout for scope-capable and collapsed nodes, then freeze the end-to-end regressions across host/canvas/shell rename flows.

## Preconditions
- `P02` is marked `PASS` in [NODE_INLINE_TITLES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_STATUS.md).
- No later `NODE_INLINE_TITLES` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/main_window_shell/edit_clipboard_history.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/main_window_shell/edit_clipboard_history.py`
- `docs/specs/work_packets/node_inline_titles/P03_scoped_title_edit_integration_WRAPUP.md`

## Required Behavior
- Make the existing header `OPEN` badge interactive for `canEnterScope` nodes and publish its hit region through the header/host interactive-rect contract so host drag/select/context and title-edit hit-testing yield correctly.
- Enable inline title editing for scope-capable nodes and collapsed nodes once the explicit `OPEN` affordance exists, so title double-click edits instead of opening scope.
- Preserve the current `nodeOpenRequested` -> `GraphCanvas.requestOpenSubnodeScope(...)` route rather than inventing a second scope-entry API.
- Keep non-scoped node behavior from `P02` intact while adding focused regressions for: scoped-node `OPEN` badge routing, collapsed title editing, and existing rename-dialog parity after the inline rollout.
- Maintain existing rename actions (`request_rename_node`, `F2`, context-menu Rename Node) and do not regress their title updates while the new inline gesture lands.

## Non-Goals
- No new bridge/controller rename APIs.
- No docs/requirements/traceability refresh in this packet.
- No new modifier gesture for scope entry; the `OPEN` badge is the preserved affordance.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "title or scope" -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/edit_clipboard_history.py --ignore=venv -k "rename_node_updates_title" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "scope" -q`

## Expected Artifacts
- `docs/specs/work_packets/node_inline_titles/P03_scoped_title_edit_integration_WRAPUP.md`

## Acceptance Criteria
- Scope-capable nodes preserve scope entry through a clickable `OPEN` badge rather than the title double-click.
- Collapsed nodes can participate in inline title editing under the shared header workflow.
- Existing rename-dialog behavior remains intact after the inline-title rollout.
- Focused host/canvas/shell regressions pass.

## Handoff Notes
- Record the final header hit-testing contract for the `OPEN` badge so later work does not accidentally treat it as ordinary title/body space.
- If any packet-owned shell regression still depends on a specific object name or header geometry assumption, document that explicitly in the wrap-up.
