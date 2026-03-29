# Cross-Process Viewer Backend Framework QA Matrix

- Updated: `2026-03-30`
- Packet set: `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK` (`P01` through `P06`)
- Scope: final closeout matrix for the shipped generic execution-side viewer backend contract, DPF temp-transport bundle materialization, shell host and binder framework, run-required reopen projection, and traceability/docs evidence.

## Locked Scope

- The worker remains the DPF authority and the UI remains the widget host; raw DPF, PyVista, and VTK objects do not cross the worker/UI boundary.
- The shipped viewer stack is registry-driven on both sides: execution uses `backend_id` plus typed `transport` descriptors, while the shell uses `ViewerHostService` plus `ViewerWidgetBinderRegistry`.
- `dpf_embedded` is the first concrete backend and binder pair under the generic framework; future backends must reuse the same `backend_id`, `transport_revision`, and blocker contract.
- Session-scoped temp transport bundles are the live-view transport even when `dpf.viewer` stays `output_mode=memory`.
- Saved `.sfe` projects retain only projection-safe viewer summary state; reopen, restore, reset, or rerun paths may project `backend_id`, `transport_revision`, and summary metadata, but live open remains blocked until rerun recreates transport.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| Execution-side backend contract, typed protocol, and worker session service | `P01` | `REQ-ARCH-016`, `REQ-EXEC-013` | `./venv/Scripts/python.exe -m pytest tests/test_execution_viewer_protocol.py tests/test_execution_client.py tests/test_execution_viewer_service.py tests/test_execution_worker.py tests/test_dpf_viewer_node.py --ignore=venv -q` | PASS in `docs/specs/work_packets/cross_process_viewer_backend_framework/P01_execution_viewer_backend_contract_WRAPUP.md` (`0484dd65d751c18f58c3b4e1aaa829910347f70b`) |
| DPF temp transport materialization, reuse, and cleanup | `P02` | `REQ-EXEC-013`, `REQ-NODE-026`, `REQ-PERSIST-020` | `./venv/Scripts/python.exe -m pytest tests/test_execution_viewer_service.py tests/test_execution_worker.py tests/test_dpf_viewer_node.py --ignore=venv -q` | PASS in `docs/specs/work_packets/cross_process_viewer_backend_framework/P02_dpf_transport_bundle_materialization_WRAPUP.md` (`7899a7642c25c3abb83598c5f53150244fbe5177`) |
| DPF materialization helpers and worker runtime service seam | `P02` | `REQ-EXEC-013`, `REQ-PERSIST-020` | `./venv/Scripts/python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_dpf_materialization.py --ignore=venv -q` | PASS in `docs/specs/work_packets/cross_process_viewer_backend_framework/P02_dpf_transport_bundle_materialization_WRAPUP.md` (`7899a7642c25c3abb83598c5f53150244fbe5177`) |
| Shell host service, binder registry seam, and overlay ownership boundaries | `P03` | `REQ-ARCH-016`, `REQ-UI-032` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py tests/test_viewer_host_service.py --ignore=venv -q` | PASS in `docs/specs/work_packets/cross_process_viewer_backend_framework/P03_shell_viewer_host_framework_WRAPUP.md` (`100587953b4b646e3568c74a1e8a17f29d103be5`) |
| Concrete DPF binder transport adoption and deterministic cleanup | `P04` | `REQ-UI-032`, `REQ-INT-008` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py tests/test_viewer_host_service.py tests/test_dpf_viewer_widget_binder.py --ignore=venv -q` | PASS in `docs/specs/work_packets/cross_process_viewer_backend_framework/P04_dpf_widget_binder_transport_adoption_WRAPUP.md` (`87613cd542b1fb762841b4c7d7888d915b14d7cf`) |
| Run-required projection, project restore, and rerun intent forwarding | `P05` | `REQ-NODE-026`, `REQ-QA-023` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_shell_run_controller.py tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py --ignore=venv -q` | PASS in `docs/specs/work_packets/cross_process_viewer_backend_framework/P05_bridge_projection_run_required_states_WRAPUP.md` (`75152ac7290d14b55aa2753e1c9a39bacbab86ed`) |
| Viewer surface blocker messaging and host projection contract | `P05` | `REQ-UI-032`, `REQ-NODE-026` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_viewer_surface_contract.py tests/test_viewer_surface_host.py --ignore=venv -q` | PASS in `docs/specs/work_packets/cross_process_viewer_backend_framework/P05_bridge_projection_run_required_states_WRAPUP.md` (`75152ac7290d14b55aa2753e1c9a39bacbab86ed`) |

## 2026-03-30 Execution Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability tests confirmed the new QA matrix, requirement anchors, and traceability rows for the cross-process viewer backend framework closeout surface |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the index, requirement docs, QA matrix, and traceability refresh landed in the packet worktree |

## Manual `dene3.sfe` Checks

1. Desktop live-open check: start the app in a native desktop Qt session, open an operator-supplied `dene3.sfe`, run the workspace that owns the DPF viewer node, and confirm the live viewer binds successfully through the shell host path even when the node remains `output_mode=memory`.
2. Reopen blocked-state check: save and close `dene3.sfe`, reopen it without rerunning, and confirm the viewer surface preserves projection-safe summary plus `backend_id` metadata while showing an explicit rerun-required blocker instead of a blank or stale live widget.
3. Rerun and rebind check: rerun the reopened workflow and confirm the rerun-required blocker clears, the viewer rebinds against a new `transport_revision`, and the previous native widget does not remain attached underneath the refreshed surface.
4. Cleanup and invalidation check: after a live bind, trigger project replacement, worker reset, or viewer invalidation and confirm the shell tears down the bound widget cleanly and the worker-side temp transport bundle is not reused after the session becomes invalid.

## Residual Desktop-Only Validation

- Real `QtInteractor`, PyVista, and VTK widget binding is only covered manually on a native desktop compositor; the retained automated packet coverage runs offscreen or against doubles.
- The `dene3.sfe` manual path is operator-supplied rather than a repo fixture, so reopen and rerun behavior against that exact project is not part of the automated fast lane.
- Temp-bundle cleanup under real filesystem locks, shell close order, and native widget teardown timing still needs desktop confirmation when validating a release candidate.

## Residual Risks

- The closeout evidence is intentionally assembled from retained `P01` through `P05` wrap-up verification plus the `P06` docs and traceability gates; this packet does not rerun a single broader aggregate suite outside its declared verification commands.
- Windows packaged-build follow-up for the viewer extras remains documented by the historical `PYDPF_VIEWER_V1` matrix and packaging coverage, not by a fresh package build in this packet.
