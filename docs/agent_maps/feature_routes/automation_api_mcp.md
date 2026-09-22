# Automation API And MCP Server

Lookup aliases: `automation api`, `mcp server`, `corex-mcp`, `agent automation`, `CorexClient`, `graph.apply`, `--automation`, `private instance`, `automation handlers`.

## Purpose
Use this for the public programmatic control surface of COREX: the loopback NDJSON automation protocol, the declarative op catalog, the GUI-thread bridge and per-domain handlers that call existing owners, the stdlib `CorexClient` + launcher (`auto` / `attach` / `private` modes), and the `corex-mcp` MCP server with embedded agent guidance. It is a local opt-in developer automation surface, not permissioned agent orchestration (`REQ-ARCH-020/EXEC-022/UI-058` stay blocked).

## Start Here
- `ea_node_editor/automation/op_catalog.py` and `ea_node_editor/automation/ops/` (single source of truth for op names, params, results, flags, MCP tool names)
- `ea_node_editor/automation/protocol.py`, `ea_node_editor/automation/errors.py` (frozen wire contract and error codes)
- `ea_node_editor/automation/gate.py` (`COREX_AUTOMATION_*` env, token popped from `os.environ`)
- `ea_node_editor/automation/transport.py`, `ea_node_editor/automation/discovery.py` (loopback server, per-user instance files)
- `ea_node_editor/automation/client.py`, `ea_node_editor/automation/client_api/`, `ea_node_editor/automation/launcher.py`
- `ea_node_editor/automation/mcp_server.py`, `ea_node_editor/automation/guidance.py`, `ea_node_editor/automation/docgen.py`
- `ea_node_editor/ui/shell/automation/context.py` (`AutomationContext` facade + summaries), `ea_node_editor/ui/shell/automation/dispatch.py` (validate, grouped undo step, error translation)
- `ea_node_editor/ui/shell/automation/handlers/` (one module per domain, explicit `HANDLERS` tables), `ea_node_editor/ui/shell/automation/registry.py`
- `ea_node_editor/ui/shell/automation/bridge.py`, `ea_node_editor/ui/shell/automation/service.py` (GUI-thread queue + lifecycle started from `ea_node_editor/app.py`)
- `tests/automation/harness.py` (shell-free context: offscreen `GraphSceneBridge` + `RuntimeGraphHistory` + built-in registry)
- `docs/PLAN_COREX_AUTOMATION_API_MCP.md` (task ledger, blockers B1-B6, decisions)

## Do Not Start Here
- `ea_node_editor/ui/shell/composition/` for automation wiring; the server starts from `app.py` after the splash and the pinned `ShellServices` shape is untouched.
- `ea_node_editor/graph/model.py` private record writers or `GraphRecordMutation` for handler mutations; handlers go through `host.scene` (`GraphSceneBridge`) and the navigation / document-IO seams.
- `ea_node_editor/ui/shell/controllers/graph_action_controller.py` `trigger` for automation; many action ids open dialogs or touch the OS clipboard.
- `ea_node_editor/execution/` for run polling; `run.status` polls `ShellRunState` from a bridge-owned timer (the repo pins the `execution_event` connect count at 1).

## Common Changes
- New op: add an `OpSpec` to the domain module under `ops/`, add the handler to the matching `handlers/<domain>.py` `HANDLERS` table, add a `client_api` method, regenerate the guide reference (`docgen`), extend `tests/automation/test_catalog.py` expectations.
- New error code: append to `errors.ERROR_CODES` with an imperative default hint; document in the guide.
- Dialog-free seams used by handlers: `WorkspaceNavigationController.create_workspace_named` / `rename_workspace_to` / `close_workspace_noninteractive`, `WorkspaceViewNavOps.create_view_named` / `rename_view_to` / `close_view(show_errors=False)`, `ProjectDocumentIOService.save_project_to_path` / `open_project_path_noninteractive` / `new_project_noninteractive` / `document_io_active`.
- Capture: `CanvasExportPresenter.capture_canvas_view_pngs` renders offscreen only when node shadows are disabled during the grab (`ShellWorkspacePresenter.set_graphics_node_shadow`); shared numeric helpers live in `ea_node_editor/ui/canvas_view_export.py` (`positive_capture_dimension`).
- Spawned instances: `COREX_SESSION_STATE_DIR` (settings seam) isolates autosave / last-session / staging; `EA_NODE_EDITOR_BOOTSTRAPPED=1` skips the venv re-exec so the launcher-generated instance id matches discovery.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/automation -q -n 0
.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_dead_code_hygiene.py tests/test_canvas_export_presenter.py -q
```

## Breadcrumbs
- [Clipboard, Undo, Redo, And Mutation History](clipboard_undo_redo_mutation_history.md)
- [Graph Actions And Context Menus](graph_actions_and_context_menus.md)
- [Workspace Tabs And Library Context Menus](workspace_tabs_library_context_menus.md)
- [Project Session, Project Files, And Node Files](project_session_files_managed_artifacts.md)
- [Run Controller And Selected Workspace State](run_controller_selected_workspace_state.md)
- [Shell Startup, QML Context, And Splash](shell_startup_qml_context_splash.md)
- [Startup, Bootstrap, And App Lifecycle](../subsystems/startup_and_bootstrap.md)

## Update Triggers
Update when the op catalog, wire protocol, error codes, launch modes, discovery layout, handler ownership, dialog-free seams, MCP tool surface, or the guide/skill install path changes.
