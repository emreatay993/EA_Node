# COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION Work Packet Manifest

- Date: `2026-04-24`
- Integration base: `main`
- Published packet window: `P00` through `P05`
- Scope baseline: convert [PLANS_TO_IMPLEMENT/in_progress/COREX Architecture Entry Point Reduction Plan.md](../../../../PLANS_TO_IMPLEMENT/in_progress/COREX%20Architecture%20Entry%20Point%20Reduction%20Plan.md) into an execution-ready packet set that reduces graph UI action breadcrumbing by merging menu, shortcut, QML context-menu, and node-delegate action routes behind one internal graph action contract, controller, and QML bridge.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/COREX Architecture Entry Point Reduction Plan.md](../../../../PLANS_TO_IMPLEMENT/in_progress/COREX%20Architecture%20Entry%20Point%20Reduction%20Plan.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `ARCHITECTURE.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/UI_CONTEXT_SCALABILITY_REFACTOR_MANIFEST.md`
- `docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md`

## Retained Packet Order

1. `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P00_bootstrap.md`
2. `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P01_action_inventory_guardrails.md`
3. `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P02_canonical_controller_and_bridge.md`
4. `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P03_pyqt_action_route_merge.md`
5. `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P04_qml_action_route_merge.md`
6. `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P05_closeout_docs_and_metrics.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/corex-architecture-entry-point-reduction/p00-bootstrap` | Establish packet docs, status ledger, execution waves, standalone prompts, and spec-index registration |
| P01 Action Inventory Guardrails | `codex/corex-architecture-entry-point-reduction/p01-action-inventory-guardrails` | Create the canonical graph action contract and static guardrails before behavior routes move |
| P02 Canonical Controller and Bridge | `codex/corex-architecture-entry-point-reduction/p02-canonical-controller-and-bridge` | Add the internal graph action owner and QML-facing bridge while old routes still work |
| P03 PyQt Action Route Merge | `codex/corex-architecture-entry-point-reduction/p03-pyqt-action-route-merge` | Route shell menu actions and shortcuts through the canonical controller and retire redundant PyQt wrappers when safe |
| P04 QML Action Route Merge | `codex/corex-architecture-entry-point-reduction/p04-qml-action-route-merge` | Route graph context menus and node delegate actions through the canonical bridge and retire obsolete high-level QML command slots |
| P05 Closeout Docs and Metrics | `codex/corex-architecture-entry-point-reduction/p05-closeout-docs-and-metrics` | Publish architecture ownership docs, QA evidence, and entry-point reduction metrics |

## Worker Agent Defaults

- Implementation workers for `P01` through `P05` must be spawned with `model="gpt-5.5"` and `reasoning_effort="xhigh"`.
- Exploratory subagents may use `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point discovery.
- Spark may be used only for one exact non-editing lookup in a known file family.

## Locked Defaults

- No user-visible capability, menu label, shortcut, context-menu item, project schema, launch command, or saved-project behavior may regress.
- The cleanup strategy is aggressive internal merge: remove duplicate internal routes after the packet proves the replacement route, but keep compatibility names that current app QML, PyQt, or tests still require.
- The canonical owner for high-level graph UI actions is `GraphActionController`; QML reaches it through `GraphActionBridge`.
- Low-level canvas operations remain outside the new action controller: selection, node movement, node resize, viewport operations, port drag, geometry updates, and direct scene policy checks stay in their existing bridge/service owners.
- Later packets inherit earlier regression anchors when they change a seam asserted by those tests. Update inherited tests in the later packet instead of leaving stale assertions behind.
- Packet execution is sequential because each packet intentionally touches shared graph action contracts or shell/QML bridge assertions.
- Verification commands use the project venv: `.\venv\Scripts\python.exe`.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

### Wave 4
- `P04`

### Wave 5
- `P05`

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/COREX Architecture Entry Point Reduction Plan.md`
- Manifest: `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_MANIFEST.md`
- Status ledger: `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_STATUS.md`
- Packet specs: `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P00_bootstrap.md` through `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P05_closeout_docs_and_metrics.md`
- Packet prompts: matching `*_PROMPT.md` files for `P00` through `P05`
- Packet wrap-ups: `P01_action_inventory_guardrails_WRAPUP.md` through `P05_closeout_docs_and_metrics_WRAPUP.md`
- Primary source anchors: `ea_node_editor/ui/shell/window_actions.py`, `ea_node_editor/ui/shell/window_state/workspace_graph_actions.py`, `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- Primary regression anchors: `tests/test_main_window_shell.py`, `tests/main_window_shell/bridge_contracts_graph_canvas.py`, `tests/main_window_shell/comment_backdrop_workflows.py`, `tests/main_window_shell/passive_style_context_menus.py`, `tests/test_graph_scene_bridge_bind_regression.py`

## Standard Thread Prompt Shell

```text
Implement COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_PXX_<name>.md exactly. Before editing, read COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_MANIFEST.md, COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_STATUS.md, and COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.
```

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
- Executor-spawned implementation workers must use `gpt-5.5` with `xhigh` reasoning for this packet set.
