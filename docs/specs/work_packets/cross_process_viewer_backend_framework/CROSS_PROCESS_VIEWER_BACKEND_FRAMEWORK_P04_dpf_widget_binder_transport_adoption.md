# CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK P04: DPF Widget Binder Transport Adoption

## Objective

- Implement the first concrete DPF widget binder so the shell host framework creates or reuses `QtInteractor`, loads the worker-prepared temp transport bundle, applies initial camera or playback state, and rebinds deterministically when transport revision or live-mode state changes.

## Preconditions

- `P03` is complete and the shell host/binder framework is available.
- The implementation base is current `main`.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/ui_qml/viewer_host*.py`
- `ea_node_editor/ui_qml/viewer_widget_binder*.py`
- `ea_node_editor/ui_qml/dpf_viewer*.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `tests/test_viewer_host_service.py`
- `tests/test_dpf_viewer_widget_binder.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/viewer_host*.py`
- `ea_node_editor/ui_qml/viewer_widget_binder*.py`
- `ea_node_editor/ui_qml/dpf_viewer*.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `tests/test_viewer_host_service.py`
- `tests/test_dpf_viewer_widget_binder.py`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/P04_dpf_widget_binder_transport_adoption_WRAPUP.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md`

## Required Behavior

- Implement the first concrete DPF binder keyed by `backend_id` on top of the host framework from `P03`.
- Make the binder create or reuse `QtInteractor`, load the worker-prepared temp transport bundle and metadata, and apply the authoritative session camera or playback snapshot during bind.
- Rebind or clear deterministically on promotion, demotion, close, and `transport_revision` changes instead of leaving stale live widgets behind.
- Treat missing or blocked live transport as a no-bind condition with explicit cleanup rather than an empty persistent native widget.
- Update inherited host or overlay regression anchors in place and add packet-owned fake-interactor proof that the binder loads transport content instead of only instantiating a widget shell.

## Non-Goals

- No generic non-DPF backend implementations yet.
- No bridge user-copy or project-load blocker messaging yet; that belongs to `P05`.
- No requirement-doc or traceability updates yet.

## Verification Commands

1. Binder verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py tests/test_viewer_host_service.py tests/test_dpf_viewer_widget_binder.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_dpf_viewer_widget_binder.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/cross_process_viewer_backend_framework/P04_dpf_widget_binder_transport_adoption_WRAPUP.md`
- `ea_node_editor/ui_qml/viewer_host*.py`
- `ea_node_editor/ui_qml/viewer_widget_binder*.py`
- `ea_node_editor/ui_qml/dpf_viewer*.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `tests/test_viewer_host_service.py`
- `tests/test_dpf_viewer_widget_binder.py`

## Acceptance Criteria

- The DPF binder loads worker-prepared transport into `QtInteractor` rather than leaving a blank live widget.
- Binder lifecycle tracks promotion, demotion, close, and transport revision updates deterministically.
- Missing or blocked transport tears down or suppresses live binding cleanly.
- The packet-owned binder verification passes.
- The review gate passes.

## Handoff Notes

- Stop after `P04`. Do not start `P05` in the same thread.
- `P05` inherits packet-owned bridge or viewer-surface tests when the user-visible run-required projection changes the surface contract.
