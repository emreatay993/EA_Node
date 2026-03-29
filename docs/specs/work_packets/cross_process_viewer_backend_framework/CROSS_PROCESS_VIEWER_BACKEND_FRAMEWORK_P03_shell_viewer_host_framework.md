# CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK P03: Shell Viewer Host Framework

## Objective

- Add the shell-owned viewer host/binder framework between the projected session bridge and the overlay manager, and reduce the overlay manager to widget/container lifecycle, visibility, and geometry only.

## Preconditions

- `P02` is complete and the execution-side transport contract is available to the shell.
- The implementation base is current `main`.

## Execution Dependencies

- `P02`

## Target Subsystems

- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `ea_node_editor/ui_qml/viewer_host*.py`
- `ea_node_editor/ui_qml/viewer_widget_binder*.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `tests/test_viewer_host_service.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `ea_node_editor/ui_qml/viewer_host*.py`
- `ea_node_editor/ui_qml/viewer_widget_binder*.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `tests/test_viewer_host_service.py`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/P03_shell_viewer_host_framework_WRAPUP.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md`

## Required Behavior

- Add a shell-owned viewer host service that consumes projected session state, owns binder registration keyed by `backend_id`, and coordinates widget binding separately from the bridge and overlay manager.
- Reduce `embedded_viewer_overlay_manager.py` to container/widget lifecycle, visibility, and geometry; it must not interpret backend payloads or decide how renderer content is populated.
- Add a generic widget-binder interface or registry that later packets can implement without special-casing DPF in the overlay manager.
- Wire host-service lifetime and discovery through `ShellWindow` and shell composition so QML and shell startup own one host-service path.
- Update inherited overlay regression anchors in place and add packet-owned host-service coverage without duplicating the same geometry assertions across multiple test files.

## Non-Goals

- No DPF binder transport loading yet; that belongs to `P04`.
- No bridge user-copy or run-required state work yet; that belongs to `P05`.
- No requirement-doc or traceability updates yet.

## Verification Commands

1. Host framework verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py tests/test_viewer_host_service.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py tests/test_viewer_host_service.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/cross_process_viewer_backend_framework/P03_shell_viewer_host_framework_WRAPUP.md`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `ea_node_editor/ui_qml/viewer_host*.py`
- `ea_node_editor/ui_qml/viewer_widget_binder*.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `tests/test_viewer_host_service.py`

## Acceptance Criteria

- The shell owns a dedicated viewer host service between the bridge and overlay manager.
- The overlay manager is geometry and widget-container infrastructure only after this packet.
- Binder registration is generic and keyed by `backend_id`.
- The packet-owned host/overlay verification passes.
- The review gate passes.

## Handoff Notes

- Stop after `P03`. Do not start `P04` in the same thread.
- `P04` inherits `tests/test_embedded_viewer_overlay_manager.py` and `tests/test_viewer_host_service.py` when it adds the first concrete DPF binder behavior on top of this framework.
