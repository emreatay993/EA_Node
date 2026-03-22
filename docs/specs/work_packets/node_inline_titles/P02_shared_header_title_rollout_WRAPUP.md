# P02 Shared Header Title Rollout Wrap-Up

## Implementation Summary

- Packet: `P02`
- Branch Label: `codex/node-inline-titles/p02-shared-header-title-rollout`
- Commit Owner: `worker`
- Commit SHA: `b33a9e1ecbd27e41ba7654961e08916aa9ebe917`
- Changed Files: `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, `tests/test_passive_graph_surface_host.py`, `tests/test_graph_surface_input_contract.py`, `docs/specs/work_packets/node_inline_titles/P02_shared_header_title_rollout_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/node_inline_titles/P02_shared_header_title_rollout_WRAPUP.md`, `tests/test_passive_graph_surface_host.py`, `tests/test_graph_surface_input_contract.py`

`GraphNodeHost` now exposes a packet-owned `sharedHeaderTitleEditable` capability for any node with data that is neither collapsed nor scope-capable. `GraphNodeHeaderLayer` now keys the shared header editor, title hit region, and editor interaction region off that generic capability instead of the former flowchart-only gate, while leaving the existing `flowchartTitleEditable` alias in place for the flowchart surface path.

The rollout reuses the existing shared header editor and `inlinePropertyCommitted(nodeId, "title", value)` signal path without adding a title-specific bridge or a surface-local editor. Non-scoped standard executable nodes and passive non-flowchart nodes now enter the same shared header title editor on title double-click, keep single-click title selection intact, commit on Enter or external focus-loss interaction, cancel on Escape, and preserve body double-click fallback to the existing open route. Scope-capable nodes remain excluded for `P03`.

Focused regressions now cover the widened host behavior and the real canvas delegate path. The host probes verify standard and passive non-scoped nodes for activation, commit, cancel, pointer isolation, and preserved non-title double-click behavior, plus a guard that scope-capable nodes still stay on the old open path. The canvas probe verifies the `GraphCanvas` delegate uses the same shared header request/commit helpers and still routes title commits through the existing selection plus `set_node_property(nodeId, "title", value)` bridge.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "title" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch this branch on a graph that contains a non-scoped standard executable node, a non-scoped passive non-flowchart node, and a scope-capable node.
- Action: single-click the standard node title, then double-click it. Expected result: single-click only selects the node; double-click opens the shared header title editor in place without opening scope or changing the body double-click behavior.
- Action: rename the standard node title once with `Enter` and once by clicking outside the editor. Expected result: both paths commit the trimmed title through the normal rename/property route and the editor closes after each commit.
- Action: open the passive node title editor, then click, double-click, and right-click inside the text field before pressing `Escape`. Expected result: pointer activity stays inside the editor, no node-open or context-menu action leaks through, and `Escape` cancels the edit.
- Action: double-click the title of the scope-capable node. Expected result: it stays on the existing open path and does not enter the shared title editor on this packet branch.

## Residual Risks

- `P02` intentionally leaves collapsed-node and scope-capable inline title editing to `P03`, so those paths still use the pre-rollout behavior.
- Verification is focused on QML host/canvas regressions; no broader interactive desktop smoke run was performed on this branch.

## Ready for Integration

- Yes: the packet stayed inside its assigned scope, widened the existing shared header editor instead of creating a second title-edit path, preserved the `P03` exclusions for scoped/collapsed nodes, and passed the required verification commands.
