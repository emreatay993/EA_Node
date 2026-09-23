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
- Environmental: `tests/test_packaging_configuration.py::`
  `test_windows_package_dependency_probe_executes_exact_python_and_xy_gate`
  requires `pwsh` (PowerShell 7) on PATH, which this machine lacks; it fails
  identically on the unmodified tree.

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
| B8 (new) | Every real `--automation` launch died with 0xC0000409 right after the splash: `app.aboutToQuit.connect(service.stop)` raised `TypeError` (a `slots=True` dataclass is not weak-referenceable) inside the `_finish_startup` QTimer slot, which PyQt6 escalates to a fatal abort with no traceback | `AutomationService` is `@dataclass(slots=True, weakref_slot=True)`; regression test connects `service.stop` to a real Qt signal (`tests/automation/test_bridge.py`) |
| B9 (new, pre-existing product bug) | A start with no restorable session and no autosave (first run, every isolated private instance) never called `_install_project`, so the runtime had no project solution namespace and the first Save failed with `save_solution_stage_failed` | `ProjectDocumentIOService.activate_project_solution_session` extracted from `_install_project` and called by `restore_session` when nothing was restored; regression test in `tests/test_project_session_controller_unit.py` |
| B10 (new) | `AutomationContext` cached `host.model` / `host.workspace_manager` / `host.registry`, but project open/new and plugin reload replace them, so every op after `project.open` acted on the old project | `model`, `registry`, `workspace_manager` are live properties read from `host`; `stored_*` fields are the shell-free fallback; tests in `test_automation_boundaries.py` and `test_handlers_shell.py` |
| B11 (new) | Flowchart shapes draw `properties.body` (defaulting to the shape name), so a title set by automation was stored but not visible (found by a real private-instance screenshot) | On the classic shapes (start, end, process, decision, document, connector, input_output, predefined_process, database) `node.add` / `node.update` titles also set an untouched body; explicit or customised bodies win; decorative shapes keep `body` as separate content |
| B12 (new) | `corex-mcp` connected to COREX before answering the MCP handshake; a private spawn takes 10-20 s, longer than typical client startup timeouts | `LazyCorexClient`: connect on the first tool call, connection failures are ordinary tool errors, a lost connection reconnects |

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
| T01 | Transport, gate, discovery | worker | DONE 2026-09-22 (51 tests; adds protocol-version check in hello, `bound_address`, instance-id validation, explicit-id lookup never falls back) |
| T02 | Bridge (FIFO, guards, watchdog, deferred poller), service, registry | worker | DONE 2026-09-22 (21 tests; stop order is discovery file -> bridge -> server so parked reader threads wake; queued requests whose `timeout_s` elapsed are not executed) |
| T03 | Navigation dialog-free cores | worker | DONE 2026-09-22 (14 tests; `WorkspaceCloseOutcome`, `create_workspace_named`, `rename_workspace_to`, `close_workspace_noninteractive`, `create_view_named`, `rename_view_to`, `close_view(show_errors=)`) |
| T04 | Non-interactive document IO + `COREX_SESSION_STATE_DIR` | worker | DONE 2026-09-22 (13 tests; `ProjectOpenResult`, reason code `save_path_required`, `session_state_dir()`) |
| T05 | Node / catalog / graph-read handlers + client facades | worker | DONE 2026-09-22 (26 tests; passive titles are property-backed, text node content key is `text`, media source port unexposed on create, propagate follows edges) |
| T06 | Edge / structure / layout handlers + client facades | worker | DONE 2026-09-22 (21 tests; data inputs single-connection, `replace_existing` replaces all edges on the port, edge style aliases) |
| T07 | Comment / link handlers + client facade | worker | DONE 2026-09-22 (20 tests; comment edits keep stored author/flags unless supplied) |
| T08 | `CorexClient` core + launcher | worker | DONE 2026-09-22 (33 tests; connect-phase failures are `NOT_FOUND`, `terminate()` only cleans owned instances, `close(quit_owned_instance=False)` detaches) |
| T09 | Workspace / view / project / run / capture / app handlers | worker | DONE 2026-09-23 (21 real-shell tests; `app.quit` checks PROJECT_DIRTY itself because closeEvent never prompts; `run.start` only refuses an in-flight run, not a queued auto-run; undo labels are not observable after the scene refresh) |
| T10 | MCP server + guidance | worker | DONE 2026-09-23 (31 tests incl. a real in-memory MCP session; 47 tools, 4 `corex://` resources, 2 prompts; lazy connect added by the coordinator) |
| T11 | `graph.apply` | worker | DONE 2026-09-23 (19 tests; atomic failure restores snapshot/scope/selection and raises APPLY_FAILED with no undo entry; atomic=false keeps applied ops as one undo step) |
| T12 | Guide, docgen, examples, skill + installer | worker | DONE 2026-09-23 (`docs/AUTOMATION_API_GUIDE.md` with a docgen-generated reference block guarded by `tests/automation/test_docgen.py`; four examples; skill + installer) |
| T13 | Integration: bootstrap flags, app start hook, pyproject `[mcp]` + `corex-mcp`, shell-isolation target, e2e private-instance test, index regeneration, spec registration, README | coordinator | DONE 2026-09-23 (see verification record) |

Per-wave independent review:

- Wave 1 (2026-09-22): 14 findings. Fixed: `auto` spawns shared the user's session state (every spawn now gets its own `COREX_SESSION_STATE_DIR`; an owned visible instance is only quit when it is clean, otherwise detached); `node.update` / `link.upsert` mutated before validating (validation hoisted, failed ops leave no undo entry); `auto` attached to other clients' private instances (visible only); stale discovery records after PID reuse (liveness also probes the port); token in dataclass reprs (`repr=False`); client socket timeout leaked into the next send; unknown edge style keys were silently dropped; missing test banners; B3 staged-file save untested; token pop timing (gate imported in `bootstrap.main`). Documented instead of fixed: inline `html` for web panels lives in session staging and is not packed into the `.cxproj`.
- Final review (Wave 2 + integration): recorded in the verification record below.

## Verification record

- T00 (2026-09-22): `tests/automation` (protocol, catalog, boundaries) green
  serially; `tests/test_canvas_export_presenter.py` + `tests/test_media_panel_action_service.py`
  green except the pre-existing baseline failure listed above;
  `scripts/check_agent_maps.py`, `tests/test_agent_route_index.py`,
  `tests/test_architecture_boundaries.py`, `tests/test_dead_code_hygiene.py`
  results recorded in the T00 commit message.
- Waves 1-2 + T13 (2026-09-23, serial `-n 0`):
  - `tests/automation` without the spawned test: 331 passed (includes the real
    `ShellWindow` suite `tests/automation/test_handlers_shell.py`).
  - `tests/automation/test_e2e_private_instance.py`: passed in ~20 s against a
    spawned private headless COREX (build with `graph.apply`, style, group,
    comment, link, subnode, save, new, reopen, non-blank screenshot, quit).
  - All four `examples/automation/*.py` pass with `--mode private` (the run
    example completes a real process-isolated run and logs the node output).
  - Gate set (412 passed): `test_architecture_boundaries`, `test_dead_code_hygiene`,
    `test_main_bootstrap`, `test_packaging_configuration`, `test_agent_route_index`,
    `test_agent_maps_hygiene`, `test_markdown_hygiene`, `test_traceability_checker`,
    `test_source_test_file_index`, `test_run_verification`, capture owners, the
    navigation and project-session suites; the only failures are the three
    baseline/environmental ones listed under Baseline.
  - `scripts/check_agent_maps.py`, `check_markdown_links.py`,
    `check_traceability.py`: pass.
  - `tests/test_shell_isolation_phase.py` catalog tests and the new
    `main_window__automation_shell_handlers` target pass. Two catalog tests
    fail on a pre-existing gap: commit `03c2b483` added
    `test_graph_search_close_returns_keyboard_focus_to_canvas` to
    `tests/main_window_shell/shell_basics_and_search.py` without a
    shell-isolation target (out of scope; left unchanged).

## First-pass limits (documented for agents)

- Graph ops act on the active workspace and open scope.
- Web panels and 3D viewers are not rendered in offscreen screenshots
  (`fidelity=offscreen_layout`); use `private` with `headless=False` or
  `attach` for native fidelity.
- A failed run refocuses the canvas on the failed node (existing UI behaviour).
- `graph.apply` rollback cannot undo staged files or the title-driven artifact
  folder rename.
- Frozen (PyInstaller) profiles exclude the `[mcp]` extra in the first pass.
