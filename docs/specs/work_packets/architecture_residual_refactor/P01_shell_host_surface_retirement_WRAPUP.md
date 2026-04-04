## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/architecture-residual-refactor/p01-shell-host-surface-retirement`
- Commit Owner: `worker`
- Commit SHA: `167c2c7aae6bc91959cece14b2a0dcb8b8d14768`
- Changed Files: `docs/specs/work_packets/architecture_residual_refactor/P01_shell_host_surface_retirement_WRAPUP.md`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui/shell/controllers/project_session_controller.py`, `ea_node_editor/ui/shell/controllers/run_controller.py`, `ea_node_editor/ui/shell/presenters.py`, `tests/test_main_bootstrap.py`, `tests/test_project_session_controller_unit.py`
- Artifacts Produced: `docs/specs/work_packets/architecture_residual_refactor/P01_shell_host_surface_retirement_WRAPUP.md`

- Added composition-owned shell host adapter classes so `WorkspaceLibraryController`, `ProjectSessionController`, `RunController`, and the packet-owned presenters are constructed against focused adapter seams instead of the raw `ShellWindow`.
- Updated packet-owned presenter construction to accept an explicit Qt parent separately from the host contract, which lets composition inject focused runtime surfaces without changing live widget ownership.
- Narrowed project-session dialog and node-path browsing toward presenter-owned seams by letting controller adapters expose the real dialog parent while preferring `graph_canvas_presenter.browse_node_property_path(...)` over the shell-window pass-through.
- Tightened `RunController` host typing to the workflow-settings and failed-node-focus seams it actually consumes, and added bootstrap regression coverage proving the composition bundle now wraps the live shell window in controller and presenter adapters.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_project_session_controller_unit.py tests/test_workspace_library_controller_unit.py tests/test_shell_project_session_controller.py tests/test_shell_run_controller.py tests/test_main_window_shell.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_project_session_controller_unit.py tests/test_workspace_library_controller_unit.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree build from `C:\w\ea_node_ed-p01-3ca641` with `.\venv\Scripts\python.exe main.py` in a normal desktop session.

1. Shell startup and action smoke
Action: open the application, then use the graph-search action, create a workspace, create a view, and switch between the available views and workspaces.
Expected result: the main shell loads normally, graph search opens without QML errors, and the workspace/view actions update the visible shell state without relying on a broken host pass-through.

2. Project-session path browsing smoke
Action: open or create a project with a file-backed node, then trigger the node-path browse flow from the shell UI and choose a replacement path.
Expected result: the browse flow resolves through the active presenter/controller path, the selected value is committed back to the node, and the shell stays on the expected workspace/view state.

3. Run toolbar smoke
Action: start a workflow run from the shell toolbar, then pause/resume or stop it, and watch the console/status strip update.
Expected result: run, pause, resume, and stop actions still operate correctly through the packet-owned workspace presenter and run controller surfaces, with the shell status UI remaining synchronized.

4. Passive PDF shell regression smoke
Action: add a PDF panel node, browse to a small local PDF, and confirm the panel renders while the shell remains responsive.
Expected result: the PDF panel path browse still commits through the shell host seams and no passive-PDF subprocess or payload-building error appears.

## Residual Risks

- `ShellWindow` still exposes legacy QAction slots and packet-external delegations for menu and widget wiring; this packet reduces controller and presenter host coupling, but it does not retire every remaining shell facade method.
- `WorkspaceLibraryController` still aggregates several broader subcontroller surfaces internally; this packet narrows construction ownership around the shell host, not the entire workspace-controller tree.

## Ready for Integration

- Yes: the packet-owned shell host refactor, inherited shell regressions, and packet review gate all pass on the rebased branch.
