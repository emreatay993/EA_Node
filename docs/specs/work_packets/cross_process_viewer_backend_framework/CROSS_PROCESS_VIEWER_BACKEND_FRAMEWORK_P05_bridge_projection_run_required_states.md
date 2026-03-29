# CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK P05: Bridge Projection Run-Required States

## Objective

- Reduce the viewer session bridge to projection plus intent forwarding, update project-load and rerun flows to project explicit run-required blocker state from the authoritative session path, and make the viewer surface show user-readable blocker copy instead of falling through to a blank native widget.

## Preconditions

- `P04` is complete and the DPF binder can bind or clear transport deterministically.
- The implementation base is current `main`.

## Execution Dependencies

- `P04`

## Target Subsystems

- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_shell_run_controller.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_surface_host.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_shell_run_controller.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_surface_host.py`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/P05_bridge_projection_run_required_states_WRAPUP.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md`

## Required Behavior

- Reduce `viewer_session_bridge.py` to a projection and intent-forwarding layer that consumes authoritative session payloads instead of synthesizing packet-owned authoritative state for invalidation, transport readiness, or blocker resolution.
- Project `backend_id`, typed transport metadata, `transport_revision`, and explicit live-open status or blocker fields from the authoritative session path into the bridge and viewer-surface contract.
- Update project open, restore-session, rerun, and worker-reset flows so saved-project reopen can show summary or proxy state while live open remains blocked until rerun recreates transport.
- Ensure live transport data itself is not persisted into `.sfe`; only projection-safe summary or blocker state may survive project reopen where the current architecture already carries it.
- Update `GraphViewerSurface.qml`, its contract, and host tests so the user sees explicit run-required messaging before rerun instead of a blank live pane or ambiguous placeholder.
- Update inherited bridge, run-controller, project-session, and viewer-surface regression anchors in place rather than leaving stale earlier assertions behind.

## Non-Goals

- No new backend types or additional DPF binder feature work beyond the authoritative-state projection required here.
- No requirement-doc or traceability updates yet; that belongs to `P06`.
- No new packet planning docs outside this packet's wrap-up and status entry.

## Verification Commands

1. Bridge and project-session proof:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_shell_run_controller.py tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py --ignore=venv -q
```

2. Viewer-surface contract proof:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_surface_contract.py tests/test_viewer_surface_host.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/cross_process_viewer_backend_framework/P05_bridge_projection_run_required_states_WRAPUP.md`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_shell_run_controller.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_surface_host.py`

## Acceptance Criteria

- The bridge projects authoritative viewer session payloads instead of owning a competing packet-owned state machine.
- Project reload and rerun flows expose an explicit run-required blocker before live open is possible again.
- Live transport data does not persist into `.sfe`.
- Viewer surface copy and contract tests show user-readable blocker state instead of a blank native live pane.
- Both packet verification commands pass.
- The review gate passes.

## Handoff Notes

- Stop after `P05`. Do not start `P06` in the same thread.
- `P06` updates the QA matrix, requirements, and traceability evidence for the behavior shipped through `P05`.
