# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P03: Workspace Custom Workflows

## Objective

Separate workspace ordering/active-workspace authority from workspace-scoped graph/view mutation and preserve explicit custom-workflow identity rules.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and workspace/workflow tests needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P02_graph_domain_mutation` is `PASS`.

## Execution Dependencies

- `P02_graph_domain_mutation`

## Target Subsystems

- Workspace manager and ownership resolver
- Workspace mutation handoff points
- Custom workflow identifiers and related tests

## Conservative Write Scope

- `ea_node_editor/workspace/**`
- `ea_node_editor/custom_workflows/**`
- `ea_node_editor/ui/shell/controllers/workspace_navigation_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_view_nav_ops.py`
- `tests/test_workspace*.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_workspace_manager.py`
- `tests/workspace_library_controller_unit/**`
- `tests/test_architecture_boundaries.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P03_workspace_custom_workflows_WRAPUP.md`

## Required Behavior

- Keep `WorkspaceManager` focused on workspace order and active-workspace selection.
- Keep view lifecycle and graph/view mutation behind the graph/workspace mutation service boundary.
- Keep `workspace/ownership.py` pure where possible; move load-time repair to persistence/load authority when necessary.
- Preserve explicit custom-workflow IDs, workspace tab behavior, and view restoration behavior.

## Non-Goals

- Do not rewrite graph mutation internals already owned by `P02`.
- Do not change QML workspace tab visuals except where a controller API update requires it.
- Do not alter persistence schema beyond compatibility shims needed for workspace ownership handoff.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_workspace_library_controller_unit.py tests/test_workspace_manager.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_workspace_library_controller_unit.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P03_workspace_custom_workflows_WRAPUP.md`

## Acceptance Criteria

- Workspace order and view mutation ownership are separated in code and tests.
- Custom-workflow identity behavior remains explicit and compatible.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If workspace-library assertions move during an earlier packet, update the inherited test path in this packet and record the handoff in the wrap-up.
