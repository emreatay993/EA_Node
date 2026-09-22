# COREX Automation API + MCP Server

## Summary

Add a first-pass public automation API and MCP server so AI agents (Claude Code,
Codex, Claude Desktop) can author flowcharts and workflows in COREX: create
passive / media / web / text / path-pointer / panel nodes, style them, position
and resize, rename titles and ports, wire and style edges, group, create
subnodes, collapse/expand, manage workspaces and views, add comments and links,
save, run, and screenshot; plus guidance so agents use it well.

This is a **local, opt-in developer automation surface**: off by default,
loopback only, per-instance token, started with `--automation` or spawned by the
launcher. It is *not* permissioned agent orchestration; `REQ-ARCH-020`,
`REQ-EXEC-022`, and `REQ-UI-058` stay blocked and no new REQ rows are added.
Navigation: [agent map](agent_maps/feature_routes/automation_api_mcp.md).

## Approved decisions (2026-09-21)

- Spec: plan doc + guide registered in `docs/specs/INDEX.md`; no requirement
  rows; blocked SYN-OPP-0008 requirements untouched.
- Launch modes: `auto` (attach to a COREX started with `--automation`, else
  spawn a visible one), `attach`, `private` (always spawn an isolated instance;
  offscreen by default, `headless=False` for full-fidelity rendering).
- Tool surface: the plan table (46 typed MCP tools + `graph_apply` = **47**;
  the plan header's "44 + 1" was a miscount, the table is authoritative).
- Guides: repo guide doc, runnable examples, MCP-embedded guidance, Claude +
  Codex skill (one tracked `SKILL.md` + install script; `.claude/` and
  `.codex/skills/*` are gitignored).
- Design rules (binding): one in-app server serves every mode; facade never
  re-implementation; never reach a modal dialog; normalize + verify (silent
  owner no-ops become `NO_EFFECT`); single declarative op catalog; off by
  default / loopback / token; start-stop outside composition; every mutating op
  is one undo step.

## Baseline

- Branch `main`, starting HEAD `c08788ed` (2026-09-22).
- Pre-existing dirty paths that must stay uncommitted and untouched by this
  work: `M AGENTS.md`, `M docs/specs/INDEX.md` (user hunk registering the
  Physical Simulation plan; preserve it when registering this plan),
  `?? docs/PLAN_COREX_Physical_Simulation_Backend.md`, `?? examples/HPC_V0.data/`,
  `?? scripts/Strain_Gage_Positioning/modular_version/strain_candidate_points.csv`.
- Pre-existing failing tests on unmodified `main` (verified 2026-09-22):
  `tests/test_canvas_export_presenter.py::`
  `test_capture_canvas_view_pngs_crops_to_workspace_bounds_by_default`
  (crop-rect expectation drift; reproduced with the T00 edits reverted) and
  `tests/test_architecture_boundaries.py::GraphArchitectureBoundaryTests::`
  `test_plugin_registry_contributions_have_direct_owners`
  (`BUILTIN_CONTRACT_CONTRIBUTIONS` is 18, pin says 17; no automation change
  touches `ea_node_editor/nodes`). Both stay out of scope.

## Blockers found during validation -> resolutions

| # | Finding (verified) | Resolution |
|---|---|---|
| B1 | `tests/test_architecture_boundaries.py` pins the repo-wide count of the string `execution_event` + `.connect(` at 1 | `run.wait` = bridge-owned QTimer polling `ShellRunState`; automation files never contain that string (guarded by `tests/automation/test_automation_boundaries.py`) |
| B2 | No single-instance guard: a 2nd instance restores the 1st's autosave, prompts, and on close deletes the 1st's autosave + shared staging | `COREX_SESSION_STATE_DIR` seam in `settings.py`; the launcher sets it for every spawned instance |
| B3 | `save_project()` / `open_project_path()` prompt when staged files exist | Non-interactive document-IO methods (T04) |
| B4 | Windows `os.execvpe` re-exec makes `Popen.pid != COREX pid` | Launcher sets `EA_NODE_EDITOR_BOOTSTRAPPED=1` and matches discovery by launcher-generated `instance_id` |
| B5 | `.claude/`, `.agents/`, `.codex/skills/*` are gitignored | Tracked `docs/automation/skills/corex-automation/SKILL.md` + `scripts/install_automation_skill.py` |
| B6 | Canvas capture had never been proven offscreen (presenter tests fake the grab) | T00 spike: see below |
| B7 (new) | Real `capture_canvas_view_pngs` raised `AttributeError`: commit `1ac032e9` retired the mixin that owned `_positive_capture_dimension` / `_positive_capture_integer` but `canvas_export_presenter.py` and `media_panel_action_service.py` still called them | Restored as module functions `positive_capture_dimension` / `positive_capture_integer` in `ea_node_editor/ui/canvas_view_export.py`; both callers rewired; regression tests in `tests/test_canvas_export_presenter.py` |

### T00 capture spike (2026-09-22, offscreen, real `create_shell_window()`)

- After B7, `capture_canvas_view_pngs(view_ids=[active], scale=1)` returns a
  cropped 840x210 PNG in ~0.1 s.
- With node shadows on, passive flowchart bodies are invisible offscreen (only
  grid, edge arrow, ports, faint titles); with
  `shell_workspace_presenter.set_graphics_node_shadow(False)` the same call
  renders full fidelity (rounded Start, orange-styled Process, Decision
  diamond, arrow, titles). `capture.screenshot` therefore toggles shadows off
  for the grab and restores them. Fallback: `host.quick_widget.grab()` (never
  `grabWindow()`).
- Passive flow ports are `neutral`-direction ports keyed `top|right|bottom|left`
  (`CARDINAL_PASSIVE_FLOW_PORTS`); `edge.connect` documents this.

## Frozen contract (T00)

- Wire: NDJSON over loopback TCP; first frame
  `{"op":"hello","token","client","protocol":1}` -> `{app_version, protocol,
  instance_id, pid, mode}`; requests `{"id","op","params","timeout_s"}` ->
  `{"id","ok":true,"result"}` | `{"id","ok":false,"error":{code,message,hint,
  details,retryable}}`; 8 MiB frame cap. Module: `ea_node_editor/automation/protocol.py`.
- Error codes: `ea_node_editor/automation/errors.py` (`ERROR_CODES`), each with
  an imperative default hint.
- Op catalog: `ea_node_editor/automation/ops/*` -> `op_catalog.all_ops()`;
  47 ops, 47 MCP tools, 22 `apply_allowed` ops (`tests/automation/test_catalog.py`
  pins the tool list).
- `AutomationContext` (`ea_node_editor/ui/shell/automation/context.py`): `host,
  scene, view, model, registry, workspace_manager, runtime_history, nav,
  workspace_presenter, workspace_edit, project_session, run_controller,
  run_state, console, canvas_export, effects, quick_widget, gate` + helpers
  (`active_workspace`, `require_node/edge/port`, `require_passive`,
  `spec_for`, `node_summary`, `edge_summary`, `with_selection`,
  `new_ids_since`, `require_shell`).
- Handler: `Callable[[AutomationContext, Mapping[str, Any]], dict | Deferred]`;
  each `handlers/<domain>.py` ends with an explicit `HANDLERS` dict;
  `registry.build_handler_table()` merges and asserts key set == catalog.
- Dispatch: `dispatch.execute_op(context, handlers, op, params)` validates,
  wraps `mutates_graph` ops in `RuntimeGraphHistory.grouped_action`, and
  translates every exception to `AutomationOpError`.
- Bridge guards: `APP_SHUTTING_DOWN` (`host._shell_teardown_started`),
  `APP_BUSY_MODAL` (active modal/popup, retryable), `APP_BUSY`
  (`document_io_active()` + mutating op), `UNEXPECTED_DIALOG` (watchdog).
- `Deferred(poll, timeout_s, on_timeout, poll_interval_s=0.05)` polled while the
  bridge is not busy.
- `graph.apply`: `{"ops":[{"id"?,"op","params"}],"atomic":true,"label"?}`;
  `$ref` (`^\$name(\.path)?$`, `$$` escapes) resolved only in catalog
  `ref_fields`; static validation before any mutation; one grouped action;
  atomic failure restores the pre-batch workspace snapshot inside the group;
  <= 500 ops; active workspace + `apply_allowed` ops only.

## Execution tasks and ledger

| Task | Scope | Owner | Status |
|---|---|---|---|
| T00 | Contract freeze, skeleton, harness, T00 tests, spike, B7 fix, agent map, plan doc | coordinator | **DONE 2026-09-22** (commit pending) |
| T01 | Transport, gate, discovery | worker | PENDING |
| T02 | Bridge (FIFO, guards, watchdog, deferred poller), service, registry | worker | PENDING |
| T03 | Navigation dialog-free cores | worker | PENDING |
| T04 | Non-interactive document IO + `COREX_SESSION_STATE_DIR` | worker | PENDING |
| T05 | Node / catalog / graph-read handlers + client facades | worker | PENDING |
| T06 | Edge / structure / layout handlers + client facades | worker | PENDING |
| T07 | Comment / link handlers + client facade | worker | PENDING |
| T08 | `CorexClient` core + launcher | worker | PENDING |
| T09 | Workspace / view / project / run / capture / app handlers | worker | PENDING (after T02/T03/T04) |
| T10 | MCP server + guidance | worker | PENDING (after T02, T08) |
| T11 | `graph.apply` | worker | PENDING (after T05-T07) |
| T12 | Guide, docgen, examples, skill + installer | worker | PENDING |
| T13 | Integration: bootstrap flags, app start hook, pyproject `[mcp]` + `corex-mcp`, shell-isolation target, e2e private-instance test, index regeneration, spec registration, README | coordinator | PENDING |

Per-wave independent review is recorded below as it happens.

## Verification record

- T00 (2026-09-22): `tests/automation` (protocol, catalog, boundaries) green
  serially; `tests/test_canvas_export_presenter.py` + `tests/test_media_panel_action_service.py`
  green except the pre-existing baseline failure listed above;
  `scripts/check_agent_maps.py`, `tests/test_agent_route_index.py`,
  `tests/test_architecture_boundaries.py`, `tests/test_dead_code_hygiene.py`
  results recorded in the T00 commit message.

## First-pass limits (documented for agents)

- Graph ops act on the active workspace and open scope.
- Web panels and 3D viewers are not rendered in offscreen screenshots
  (`fidelity=offscreen_layout`); use `private` with `headless=False` or
  `attach` for native fidelity.
- A failed run refocuses the canvas on the failed node (existing UI behaviour).
- `graph.apply` rollback cannot undo staged files or the title-driven artifact
  folder rename.
- Frozen (PyInstaller) profiles exclude the `[mcp]` extra in the first pass.
