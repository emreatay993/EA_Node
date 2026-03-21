# P04 Flowchart Drop Connect Insert Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/flowchart-cardinal-ports/p04-flowchart-drop-connect-insert`
- Commit Owner: `worker`
- Commit SHA: `2807270afe9e50cee4ae5646fb7bffad497b5a25`
- Changed Files: `ea_node_editor/ui/shell/window_library_inspector.py`, `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`, `tests/test_window_library_inspector.py`, `tests/test_workspace_library_controller_unit.py`, `tests/main_window_shell/view_library_inspector.py`, `docs/specs/work_packets/flowchart_cardinal_ports/P04_flowchart_drop_connect_insert_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/flowchart_cardinal_ports/P04_flowchart_drop_connect_insert_WRAPUP.md`, `ea_node_editor/ui/shell/window_library_inspector.py`, `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`, `tests/test_window_library_inspector.py`, `tests/test_workspace_library_controller_unit.py`, `tests/main_window_shell/view_library_inspector.py`
- Connection quick insert now treats `direction="neutral"` plus `kind="flow"` / `data_type="flow"` as a flowchart-only compatibility class, so passive flowchart nodes remain discoverable from neutral sources without changing fixed `in` / `out` filtering for non-flowchart nodes.
- Dropped-node auto-connect now preserves the existing neutral flowchart port as the edge source and chooses the inserted node's nearest-facing exposed cardinal port by scene geometry. The side ordering rule is `primary toward peer node`, then `secondary`, then `opposite secondary`, then `opposite primary`, with horizontal winning exact diagonal ties because the helper resolves `abs(dx) >= abs(dy)` first.
- Neutral edge insertion now rewires as `source -> new -> target` with deterministic inbound and outbound cardinal picks on the inserted flowchart node, and the outbound pick excludes the already-chosen inbound side whenever another exposed neutral flow port is available.
- Graph canvas drop-preview gating now accepts neutral flowchart port and edge targets through shared JS helpers, so library drag/drop preview and commit paths agree with the controller-side neutral flow selection. The `origin_side` consumption path still resolves from the selected flowchart port's stored cardinal side (`side` / cardinal key) rather than introducing a new shell bridge payload.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest tests/test_window_library_inspector.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/view_library_inspector.py --ignore=venv -q`
- PASS (Review Gate): `./venv/Scripts/python.exe -m pytest tests/test_window_library_inspector.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch, start with an empty workspace, and keep the library visible with passive flowchart nodes available.
- Drag a passive flowchart node from the library onto the `top` or `right` port of an existing passive flowchart node. Expected: the drop preview highlights that port, the created edge starts from the existing node's selected cardinal port, and the dropped node connects through its nearest-facing exposed side.
- Drag a passive flowchart node onto an existing passive flowchart edge. Expected: the original edge is removed, two new edges appear as `source -> new -> target`, and the inserted node uses distinct inbound and outbound cardinal sides when more than one exposed side is available.
- Open connection quick insert from a `top` or `left` flowchart port and choose another passive flowchart node type. Expected: the inserted node is created, the new edge still uses the originally selected `top` or `left` port as the source, and the inserted node receives the edge on the nearest-facing cardinal side.
- Repeat quick insert or library drop on a standard non-flowchart `exec_out -> exec_in` path. Expected: fixed-direction compatibility and auto-connect behavior stay unchanged.

## Residual Risks

- Exact nearest-facing side selection is center-to-center geometry based, so perfectly balanced diagonal ties resolve horizontal before vertical by design.
- This packet relies on locked defaults from `P01` through `P03`: passive flowchart ports must keep their stored cardinal `side` aligned with the `top/right/bottom/left` key for quick insert, drag/drop preview, and controller auto-connect to stay in sync.

## Ready for Integration

- Yes: the packet's verification commands and review gate passed in the assigned worktree, and the packet diff remains inside the allowed write scope.
