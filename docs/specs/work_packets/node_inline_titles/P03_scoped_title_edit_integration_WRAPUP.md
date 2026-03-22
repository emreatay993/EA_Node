# P03 Scoped Title Edit Integration Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/node-inline-titles/p03-scoped-title-edit-integration`
- Commit Owner: `worker`
- Commit SHA: `56cb94f6ede79c4facabf816518b6a2858748bd6`
- Changed Files: `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `tests/test_passive_graph_surface_host.py`, `tests/test_graph_surface_input_contract.py`, `tests/main_window_shell/edit_clipboard_history.py`, `docs/specs/work_packets/node_inline_titles/P03_scoped_title_edit_integration_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/node_inline_titles/P03_scoped_title_edit_integration_WRAPUP.md`, `tests/test_passive_graph_surface_host.py`, `tests/test_graph_surface_input_contract.py`, `tests/main_window_shell/edit_clipboard_history.py`

`GraphNodeHost.sharedHeaderTitleEditable` now covers any node with data, which unlocks the existing shared header title editor for scope-capable and collapsed nodes without creating a second rename workflow. `GraphNodeHost` also exposes `requestScopeOpenAt(localX, localY)` as the packet-owned host seam for the header badge hit test, while leaving the existing `nodeOpenRequested` signal contract intact.

`GraphNodeHeaderLayer` now makes the visual `OPEN` badge interactive for `canEnterScope` nodes and publishes that badge through the same header interactive-rect contract the host already consults. The final contract is: `titleHitRegion` stays the edit-only title double-click target, while `embeddedInteractiveRects` now combines the live title-editor rect plus the `OPEN` badge rect; `GraphNodeHost._pointInEmbeddedInteractiveRect(...)` and `GraphNodeHost._surfaceClaimsBodyInteractionAt(...)` use that combined list so drag/select/context handling yields over the badge and the active editor, but not over ordinary title text.

The badge interaction commits any in-flight inline title edit before emitting `nodeOpenRequested`, which keeps scope entry on the existing `GraphCanvas.requestOpenSubnodeScope(...)` route instead of introducing a second scope API. Focused regressions now cover scoped-node badge hit-region publication and scope routing, collapsed-node inline title commits, and rename-dialog parity for scoped and collapsed nodes through the existing `request_rename_node(...)` path.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "title or scope" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/edit_clipboard_history.py --ignore=venv -k "rename_node_updates_title" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "scope" -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch this branch in a desktop session with a graph that contains a scope-capable node such as a subnode shell, a collapsed standard node, and at least one ordinary non-scoped node.
- Action: double-click the scope-capable node title, type a new title, then click the `OPEN` badge. Expected result: the title edit commits, the editor closes, and scope entry happens through the same open flow instead of title double-click opening scope directly.
- Action: right-click or drag across the scope-capable node `OPEN` badge area. Expected result: the badge area does not leak node context, drag, or title-edit hit testing; it remains reserved for the badge affordance.
- Action: double-click the title of a collapsed standard node, rename it, and press `Enter`. Expected result: the shared header editor opens on the collapsed node and commits the trimmed title without needing expansion first.
- Action: run Rename Node from the existing dialog path on both the scope-capable node and the collapsed node. Expected result: both titles update normally and stay in sync with the inline-edited header state.

## Residual Risks

- Packet-owned automated coverage exercises the shared `request_rename_node(...)` dialog path but does not separately drive the `F2` shortcut or context-menu Rename Node UI gestures end to end on this branch.
- Verification is focused on QML host/canvas probes and the shell rename regression; no broader interactive desktop smoke run was performed.

## Ready for Integration

- Yes: the packet stayed inside its assigned scope, preserved the existing scope-entry route, enabled scoped and collapsed inline title editing with an explicit `OPEN` affordance, and passed the required verification commands plus the review gate.
