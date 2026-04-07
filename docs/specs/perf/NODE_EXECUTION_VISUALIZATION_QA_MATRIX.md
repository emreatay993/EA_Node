# Node Execution Visualization QA Matrix

- Updated: `2026-04-07`
- Packet set: retained `NODE_EXECUTION_VISUALIZATION` closeout extended by `EXECUTION_EDGE_PROGRESS_VISUALIZATION` (`P01` through `P05`)
- Scope: final closeout matrix for the shipped run-scoped node execution chrome, authored control-edge progress visualization, active-workspace filtering, in-memory-only state, and traceability/docs evidence.

## Locked Scope

- The authoritative visual reference is `docs/node_execution_visualization_alternatives.html`, and the shipped manual baseline remains the A+E-hybrid visual baseline paired with authored control-edge dim-before-progress and first-progress flash behavior on the graph canvas.
- Running/completed node chrome remains protocol-neutral: `node_started` drives the blue pulse halo and QML-local elapsed timer, `node_completed` drives the green completed flash/border and progresses authored `exec` / `completed` control edges, and `node_failed_handled` progresses authored `failed` control edges when execution continues through handlers.
- Running/completed node and authored control-edge state stays run-scoped, active-workspace-filtered, and in-memory only. The feature does not add `.sfe` persistence fields, session-restore payloads, or a second execution-visualization signal/revision channel.
- The per-run authored-edge lookup is frozen from the run-start authored workspace snapshot so the active workspace canvas stays aligned with the run snapshot even if the graph is edited mid-run.
- Running nodes use a blue pulse halo. Completed nodes emit a green completed flash and then keep a static green border until the run ends. During an active run, authored control edges that have not progressed render at `0.2` alpha and `1.4px`; the first progress transition returns the edge to its normal interaction-aware styling and emits a QML-local `240ms` base-color flash using a `+2.4px` overlay.
- Selection and preview keep their existing interaction colors and widths and must not be dimmed, but the one-shot flash can still layer on top. Data edges and passive `flow` edges remain unchanged.
- `run_started`, `run_completed`, `run_stopped`, fatal worker-reset failures, and a fresh project session clear node chrome and edge progress together. Non-fatal `run_failed` preserves the last execution context, while handled failures keep the current run visualization until the run actually ends.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| `node_failed_handled` worker event plus authored control-edge projection from the run-start snapshot | `P01` | `REQ-NODE-027`, `AC-REQ-NODE-027-01`, `REQ-QA-027` | `.\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py -k execution_edge_progress_projection --ignore=venv -q` | PASS in `docs/specs/work_packets/execution_edge_progress_visualization/P01_run_state_edge_progress_projection_WRAPUP.md` (`99f1ff6bc62814be249b44a42f200ad8a43cc626`) |
| Shared node-execution revision path, cleanup rules, and active-workspace shell filtering | `P01` | `REQ-UI-034`, `REQ-NODE-027`, `AC-REQ-NODE-027-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k execution_edge_progress_projection --ignore=venv -q` | PASS in `docs/specs/work_packets/execution_edge_progress_visualization/P01_run_state_edge_progress_projection_WRAPUP.md` (`99f1ff6bc62814be249b44a42f200ad8a43cc626`) |
| GraphCanvas bridge exposure and active-workspace canvas binding for `progressedExecutionEdgeLookup` | `P02` | `REQ-UI-034`, `REQ-NODE-027`, `REQ-QA-027` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts.py tests/test_main_window_shell.py -k execution_edge_progress_canvas --ignore=venv -q` | PASS in `docs/specs/work_packets/execution_edge_progress_visualization/P02_graph_canvas_execution_edge_bindings_WRAPUP.md` (`e3e28074fca401a88e96b70c2d3733f302fcbc52`) |
| Authored control-edge snapshot metadata, dim-before-progress state, and one-shot flash bookkeeping | `P03` | `REQ-PERF-010`, `AC-REQ-PERF-010-01`, `REQ-QA-027` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py -k execution_edge_progress_snapshot --ignore=venv -q` | PASS in `docs/specs/work_packets/execution_edge_progress_visualization/P03_execution_edge_snapshot_metadata_WRAPUP.md` (`dee8e4e1dcc1688c4565c7100c4191c924c6ab16`) |
| Real paint-path dim-before-progress rendering, `240ms` flash, handled-failure continuation, and cleanup | `P04` | `REQ-UI-034`, `AC-REQ-UI-034-01`, `REQ-QA-027` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k execution_edge_progress_visualization --ignore=venv -q` | PASS in `docs/specs/work_packets/execution_edge_progress_visualization/P04_execution_edge_renderer_highlights_WRAPUP.md` (`dc5f987054487a08153155ff259bae43ec8e8fb4`) |
| QML renderer/preference coverage for interaction-aware styling, selection/preview override, and unchanged non-control edges | `P04` | `REQ-PERF-010`, `AC-REQ-PERF-010-01`, `REQ-QA-027` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py -k execution_edge_progress_visualization --ignore=venv -q` | PASS in `docs/specs/work_packets/execution_edge_progress_visualization/P04_execution_edge_renderer_highlights_WRAPUP.md` (`dc5f987054487a08153155ff259bae43ec8e8fb4`) |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | Packet-owned traceability regression for the canonical node execution closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Review-gate proof audit for the retained requirement, QA, and traceability docs |

## 2026-04-07 Execution Results

| Command | Result | Notes |
|---|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability tests confirmed the retained node execution QA matrix, requirement anchors, and traceability rows now cover authored control-edge progress visualization plus the shipped node chrome contract |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the canonical node execution closeout path was refreshed to cite the execution-edge `P01` through `P04` evidence |

## Remaining Manual A+E-Hybrid and Execution-Edge Visual Checks

1. Running halo, timer, and dim-before-progress: open a desktop Qt session on a workspace with authored control edges, start a simple 2-3 node workflow, and confirm the active node shows the blue pulse halo plus the QML-local elapsed timer while authored control edges on the active workspace dim before they progress.
2. First progress flash and retained completed border: let a straightforward successful path run and confirm each newly progressed control edge returns to normal styling and emits one short base-color flash (`240ms`), while each completed node emits a green completed flash once and then keeps a static green border until the run ends.
3. Handled failure continuation: route execution through a handled `On Failure` branch and confirm the authored failed edge plus its continuation progress in order, each flashes once, and failure red remains the highest-priority node state while execution still continues.
4. Workspace isolation and no persistence: switch to a different workspace while a run is active or immediately after completion and confirm foreign node/edge highlights do not appear on the inactive workspace; save, reopen, or restore the project and confirm prior node/edge execution visuals do not persist.
5. Run restart and terminal cleanup: rerun the same workflow and confirm prior node chrome and edge progress clear on `run_started`; let the run complete, stop it, or force a fatal failure and confirm dimming, flash state, and node highlights all clear back to idle styling.

## Residual Desktop-Only Validation

- Offscreen automated coverage does not validate final pulse/flash intensity, perceived edge-width shifts, or border/alpha legibility across real Windows desktop compositing and dense-graph zoom levels.
- The elapsed timer and `240ms` edge flash are intentionally QML-local, so they reset if the relevant host or edge visual is fully destroyed and recreated; that behavior matches the shipped packet contract and still needs manual acceptance on any non-standard executable surface family.
- Renderer cleanup still infers run activity from the existing revision and lookup signals rather than an explicit packet-owned run-active flag; later refactors should preserve that inference or promote it deliberately before broadening the feature.
