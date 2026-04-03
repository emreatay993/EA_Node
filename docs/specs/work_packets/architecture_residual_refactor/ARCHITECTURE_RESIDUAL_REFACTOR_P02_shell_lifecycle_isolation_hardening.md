# ARCHITECTURE_RESIDUAL_REFACTOR P02: Shell Lifecycle Isolation Hardening

## Objective

- Make packet-owned shell construction and teardown deterministic enough that repeated in-process `ShellWindow` lifecycle coverage is credible without hidden global cleanup assumptions.

## Preconditions

- `P01` is marked `PASS` in [ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md](./ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_RESIDUAL_REFACTOR` packet is in progress.

## Execution Dependencies

- `P01`

## Target Subsystems

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `tests/main_window_shell/base.py`
- `tests/shell_isolation_runtime.py`
- `tests/test_shell_isolation_phase.py`
- `tests/test_shell_window_lifecycle.py`
- `scripts/verification_manifest.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `tests/main_window_shell/base.py`
- `tests/shell_isolation_runtime.py`
- `tests/test_shell_isolation_phase.py`
- `tests/test_shell_window_lifecycle.py`
- `scripts/verification_manifest.py`
- `docs/specs/work_packets/architecture_residual_refactor/P02_shell_lifecycle_isolation_hardening_WRAPUP.md`

## Required Behavior

- Make packet-owned shell construction, close, teardown, and deferred cleanup deterministic across repeated in-process lifecycle runs.
- Add focused lifecycle regression coverage that proves repeated create, show, close, and teardown cycles in one interpreter process.
- Keep the shell-isolation phase and manifest aligned with the tightened lifecycle contract without widening packet-owned proof beyond the changed shell area.
- Update inherited shell-isolation runtime anchors in place when packet-owned lifecycle expectations change.

## Non-Goals

- No graph-scene bridge decomposition yet.
- No viewer-session authority split yet beyond lifecycle cleanup needed by this packet.
- No runtime-snapshot or graph-domain boundary work yet.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py tests/shell_isolation_runtime.py tests/test_shell_isolation_phase.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py tests/shell_isolation_runtime.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_residual_refactor/P02_shell_lifecycle_isolation_hardening_WRAPUP.md`

## Acceptance Criteria

- Packet-owned shell lifecycle tests can create and close multiple `ShellWindow` instances in one interpreter process.
- The updated shell-isolation runtime and phase regressions pass.
- Packet-owned teardown does not depend on undisclosed global cleanup order.

## Handoff Notes

- `P03` can rely on this packet's deterministic shell lifecycle baseline while it decomposes the graph-scene bridge surface.
