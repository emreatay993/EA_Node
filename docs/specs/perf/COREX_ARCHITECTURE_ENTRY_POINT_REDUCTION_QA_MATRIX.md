# COREX Architecture Entry Point Reduction QA Matrix

- Updated: `2026-04-24`
- Packet set: `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION` (`P00` through `P05`)
- Scope: closeout evidence for the graph action entry-point reduction packet set, including canonical action ownership, retained packet verification, review gates, maintainability metrics, and residual compatibility seams.

## Locked Scope

- The canonical high-level graph action path is documented in `ARCHITECTURE.md`: `shortcut/menu/QML event -> GraphActionBridge or PyQt action dispatch -> GraphActionController -> existing behavior owner`.
- `GraphActionController` is the coordinator for high-level graph verbs; existing behavior owners still perform the actual work.
- `GraphActionBridge` is the QML-facing entry point for context-menu and node-delegate graph actions.
- `GraphCanvasCommandBridge`, `GraphCanvasStateBridge`, `ViewportBridge`, `GraphSceneBridge`, and focused helper modules retain low-level canvas operations such as selection mechanics, viewport motion, node geometry, port drag/connect/drop flows, inline property commits, cursor state, quick-insert placement, and scene policy checks.
- This matrix is documentation-only closeout proof. It does not authorize new graph behavior changes after accepted `P04` state.

## Packet Outcomes

| Packet | Status | Accepted Commit | Outcome | Primary Evidence |
|---|---|---|---|---|
| `P00` Bootstrap | PASS | `bootstrap-docs-uncommitted` | Packet plan, manifest, ledger, prompts, and spec index entry were published by the planner. | `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_MANIFEST.md` |
| `P01` Action Inventory Guardrails | PASS | `b447a9dcf4b01f2dabc353d95de345d8120d70b4` | Graph action IDs, metadata, legacy route names, and guardrail tests were established before route movement. | [P01 wrap-up](../work_packets/corex_architecture_entry_point_reduction/P01_action_inventory_guardrails_WRAPUP.md) |
| `P02` Canonical Controller and Bridge | PASS | `49bd3238fa548a2c61de05459f444579c6737f8c` | `GraphActionController` and `GraphActionBridge` were added while legacy PyQt and QML routes stayed operational. | [P02 wrap-up](../work_packets/corex_architecture_entry_point_reduction/P02_canonical_controller_and_bridge_WRAPUP.md) |
| `P03` PyQt Action Route Merge | PASS | `062c22257bef0dc9ee3b27bf1792bc4605424831` | Shell menu actions, shortcuts, and host request slots converge through `GraphActionController`. | [P03 wrap-up](../work_packets/corex_architecture_entry_point_reduction/P03_pyqt_action_route_merge_WRAPUP.md) |
| `P04` QML Action Route Merge | PASS | `eb04bdecbb2b4b9cabc9da74fcbafd1708adc08b` | Graph context menus and node-delegate actions route through `graphActionBridge`, and obsolete high-level context/delegate command slots were removed. | [P04 wrap-up](../work_packets/corex_architecture_entry_point_reduction/P04_qml_action_route_merge_WRAPUP.md) |
| `P05` Closeout Docs and Metrics | PASS | Recorded in `P05_closeout_docs_and_metrics_WRAPUP.md` | Architecture ownership docs, spec-index registration, this QA matrix, and closeout verification are owned by this packet. | `docs/specs/work_packets/corex_architecture_entry_point_reduction/P05_closeout_docs_and_metrics_WRAPUP.md` |

## Retained Automated Verification

| Packet | Command | Result Source |
|---|---|---|
| `P01` | `.\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py --ignore=venv -q` | PASS in the status ledger and P01 wrap-up (`7 passed`) |
| `P02` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py --ignore=venv -q` | PASS in the status ledger and P02 wrap-up (`210 passed, 4 warnings, 318 subtests passed`) |
| `P03` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/edit_clipboard_history.py tests/main_window_shell/comment_backdrop_workflows.py --ignore=venv -q` | PASS in the status ledger and P03 wrap-up (`247 passed, 4 warnings, 318 subtests passed`) |
| `P04` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/passive_style_context_menus.py tests/main_window_shell/comment_backdrop_workflows.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q` | PASS in the status ledger and P04 wrap-up (`247 passed, 4 warnings, 378 subtests passed`) |

## P05 Closeout Verification Commands

| Coverage Area | Command | Expected Coverage | Result |
|---|---|---|---|
| Markdown hygiene, traceability checker tests, and verification metadata tests | `.\venv\Scripts\python.exe -m pytest tests/test_markdown_hygiene.py tests/test_traceability_checker.py tests/test_run_verification.py --ignore=venv -q` | Revalidates repository markdown auditing, existing traceability proof tests, and the verification manifest/runner contract after P05 documentation changes. | PASS (`97 passed, 13 subtests passed`) |
| Markdown link gate | `.\venv\Scripts\python.exe scripts/check_markdown_links.py` | Confirms `ARCHITECTURE.md`, `docs/specs/INDEX.md`, this QA matrix, retained wrap-up links, and the P05 wrap-up resolve to existing local targets and valid heading anchors. | PASS (`MARKDOWN LINK CHECK PASS`) |

## Review Gates

| Gate | Command | Required Result | Owner |
|---|---|---|---|
| P05 packet verification | `.\venv\Scripts\python.exe -m pytest tests/test_markdown_hygiene.py tests/test_traceability_checker.py tests/test_run_verification.py --ignore=venv -q` | PASS before packet handoff | P05 worker |
| P05 markdown review gate | `.\venv\Scripts\python.exe scripts/check_markdown_links.py` | PASS before packet handoff and after the final wrap-up exists | P05 worker |
| Integration identity check | `git rev-parse --show-toplevel` and `git branch --show-current` | Assigned worktree and `codex/corex-architecture-entry-point-reduction/p05-closeout-docs-and-metrics` branch | P05 worker |

## Maintainability Metrics

| Metric | Static Count | Source Search | Closeout Reading |
|---|---:|---|---|
| Canonical graph action specs | 37 | `GRAPH_ACTION_SPECS` in `ea_node_editor/ui/shell/graph_action_contracts.py` | High-level graph verbs have one inventory and one metadata source. |
| QML high-level graph action surface branches routed through `graphActionBridge` | 24 | `qml_edge_context_menu=6`, `qml_node_context_menu=13`, `qml_node_delegate=4`, `qml_selection_context_menu=1` from `GRAPH_ACTION_SPECS`; implemented by `GraphCanvasContextMenus.qml` and `GraphCanvasNodeDelegate.qml` calls to `trigger_graph_action`. | Context-menu and node-delegate verbs now converge on `GraphActionBridge`. |
| QML key-handler graph action branches still routed through `GraphCanvasCommandBridge` | 3 | `GraphCanvasInputLayers.qml` still calls `request_delete_selected_graph_items`, `request_navigate_scope_parent`, and `request_navigate_scope_root`. | These are retained compatibility paths for Delete, Alt+Left, and Alt+Home until a later input-layer action-routing packet retires them. |
| High-level `GraphCanvasCommandBridge` slots removed by `P04` | 17 | `git diff d44f846...HEAD -- ea_node_editor/ui_qml/graph_canvas_command_bridge.py` | Removed context-menu and node-delegate command slots: open comment peek, wrap selection in backdrop, 6 edge verbs, publish workflow, 5 passive node style/rename/ungroup/remove verbs, and duplicate node. |
| High-level `GraphCanvasCommandBridge` slots retained for compatibility | 5 | Static search for legacy route names in `graph_canvas_command_bridge.py`, `GraphCanvasInputLayers.qml`, and `GraphCanvasNodeSurfaceBridge.qml` | Retained slots are `request_open_subnode_scope`, `request_close_comment_peek`, `request_delete_selected_graph_items`, `request_navigate_scope_parent`, and `request_navigate_scope_root`; they serve existing input-layer, surface-bridge, and packet-external callers. |
| Host-side compatibility wrapper classes retained | 1 | `ea_node_editor/ui_qml/graph_canvas_bridge.py` | `GraphCanvasBridge` remains for deferred packet-external callers while packet-owned QML uses focused bridges directly. |
| Low-level `GraphCanvasCommandBridge` methods retained | 51 | AST count of `GraphCanvasCommandBridge` methods in `ea_node_editor/ui_qml/graph_canvas_command_bridge.py` | The retained bridge is still broad because it owns low-level canvas operations and compatibility, not because it owns the canonical high-level graph action contract. |

## Residual Risks

- P05 reruns only the documentation, traceability-test, verification-metadata, and markdown-link checks required by this packet; it does not rerun the broader offscreen Qt suites already retained from `P01` through `P04`.
- Three QML input-layer key-handler graph action branches still use `GraphCanvasCommandBridge` for Delete and scope navigation. They are documented as compatibility paths and should be retired by a later input-layer action-routing packet if the project wants complete QML event convergence on `GraphActionBridge`.
- `GraphCanvasBridge` remains as one host-side compatibility wrapper for packet-external callers. Retiring it should be a separate compatibility-removal packet after callers and tests stop depending on the wrapper surface.
- Manual desktop validation of menus, shortcuts, context menus, and node-delegate toolbar actions remains inherited from the packet wrap-ups; P05 records closeout docs and static metrics rather than new display-attached interaction evidence.
