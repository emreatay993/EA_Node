# Node Execution Visualization QA Matrix

- Updated: `2026-03-31`
- Packet set: `NODE_EXECUTION_VISUALIZATION` (`P01` through `P04`)
- Scope: final closeout matrix for the shipped run-scoped running/completed node execution chrome, active-workspace bridge filtering, and traceability/docs evidence.

## Locked Scope

- The authoritative visual reference is `docs/node_execution_visualization_alternatives.html`, and the shipped manual baseline is the A+E-hybrid visual baseline: Alternative A's blue pulse halo plus Alternative E's QML-local elapsed timer, with the packet-owned green completed flash and retained green border treatment.
- The worker/execution protocol is unchanged for this feature: `node_started` and `node_completed` remain the only event sources for running/completed highlights.
- Running/completed state stays run-scoped and ephemeral on the shell/QML side; the feature does not add `.sfe` persistence fields, completed-duration storage, or worker protocol payload expansion.
- Running nodes use a blue pulse halo. Completed nodes emit a green completed flash and then keep a static green border until the run ends. Failure red remains the highest-priority visual state.
- `run_started`, `run_completed`, `run_stopped`, and fatal worker-reset failures clear the execution highlights. Non-fatal `run_failed` preserves the last execution context so the failure pulse still has run context.
- Active-workspace filtering in `GraphCanvasStateBridge` remains authoritative, so inactive workspaces do not render foreign run highlights.
- The QML-local elapsed timer derives from `isRunningNode` transitions. There is no Python monotonic timestamp bridge, and host-chrome exceptions must not mutate graph geometry, hit testing, selection semantics, or cached scene payload structure.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| Run-state projection, execution lookup cleanup, and active-workspace bridge filtering | `P01` | `REQ-NODE-027`, `AC-REQ-NODE-027-01`, `REQ-QA-027` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_run_controller_unit.py tests/main_window_shell/bridge_contracts.py -k node_execution_bridge --ignore=venv -q` | PASS in `docs/specs/work_packets/node_execution_visualization/P01_run_state_execution_projection_WRAPUP.md` (`d52ff61d4e9f255430a3239a843c30590fbbdc54`) |
| GraphCanvas execution property binding and live bridge handoff | `P02` | `REQ-NODE-027`, `AC-REQ-NODE-027-01`, `REQ-QA-027` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py -k node_execution_canvas --ignore=venv -q` | PASS in `docs/specs/work_packets/node_execution_visualization/P02_graph_canvas_execution_bindings_WRAPUP.md` (`6ed8189e7aea22cdaf86be64f0bae0d4e5474442`) |
| Running/completed chrome, completed flash/border, and failure-priority behavior | `P03` | `REQ-UI-034`, `AC-REQ-UI-034-01`, `REQ-QA-027` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_run_controller.py -k node_execution_visualization --ignore=venv -q` | PASS in `docs/specs/work_packets/node_execution_visualization/P03_node_chrome_execution_highlights_WRAPUP.md` (`6c133da2a82eaf289c39816199d28dec853f1efe`) |
| Host cache keys, QML-local elapsed timer, and execution-visualization stacking exceptions | `P03` | `REQ-PERF-010`, `AC-REQ-PERF-010-01` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py -k node_execution_visualization --ignore=venv -q` | PASS in `docs/specs/work_packets/node_execution_visualization/P03_node_chrome_execution_highlights_WRAPUP.md` (`6c133da2a82eaf289c39816199d28dec853f1efe`) |
| GraphCanvas host-chrome state priority and bridge-driven lookup revisions | `P03` | `REQ-UI-034`, `REQ-PERF-010`, `AC-REQ-PERF-010-01` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py -k node_execution_visualization --ignore=venv -q` | PASS in `docs/specs/work_packets/node_execution_visualization/P03_node_chrome_execution_highlights_WRAPUP.md` (`6c133da2a82eaf289c39816199d28dec853f1efe`) |

## 2026-03-31 Execution Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability tests confirmed the new QA matrix, requirement anchors, and traceability rows for the node execution visualization closeout surface |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the requirement docs, QA matrix, and traceability refresh landed in the packet worktree |

## Remaining Manual A+E-Hybrid Visual Checks

1. Running halo and timer: open a desktop Qt session on a workspace with standard executable nodes, start a simple 2-3 node workflow, and confirm the active node shows the blue pulse halo plus the QML-local elapsed timer below the node while it is running.
2. Completed flash and retained border: let the workflow complete successfully and confirm each completed node emits a green completed flash once and then keeps a static green border until the run ends.
3. Run restart and cleanup: rerun the same workflow and confirm prior completed borders clear on `run_started`; let the run complete or stop it manually and confirm running/completed chrome clears on `run_completed` or `run_stopped`.
4. Workspace isolation: switch to a different workspace while a run is active or immediately after completion and confirm foreign running/completed highlights do not appear on the inactive workspace.
5. Failure priority with preserved context: inject a non-fatal node failure after a node has completed and confirm the existing red failure treatment overrides the running/completed chrome while the last execution context remains understandable to the user.

## Residual Desktop-Only Validation

- Offscreen automated coverage does not validate final pulse/flash intensity, perceived border weight, or timer legibility across real Windows desktop compositing and dense-graph zoom levels.
- The elapsed timer is intentionally QML-local, so it resets if a running node host is fully destroyed and recreated; that behavior matches the shipped packet contract and still needs manual acceptance on any non-standard executable surface family.
- Closeout evidence is intentionally assembled from retained `P01` through `P03` verification plus the `P04` traceability gate; this packet does not claim a broader rerun than the packet spec requires.
