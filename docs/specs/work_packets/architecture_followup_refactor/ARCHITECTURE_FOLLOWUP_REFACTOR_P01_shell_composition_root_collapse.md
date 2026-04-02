# ARCHITECTURE_FOLLOWUP_REFACTOR P01: Shell Composition Root Collapse

## Objective

- Reduce `ShellWindow` to top-level Qt host, lifecycle, and event wiring responsibilities so `composition.py` becomes the only packet-owned composition root for shell assembly.

## Preconditions

- `P00` is marked `PASS` in [ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md](./ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_FOLLOWUP_REFACTOR` packet is in progress.

## Execution Dependencies

- `P00`

## Target Subsystems

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/shell_runtime_contracts.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `docs/specs/work_packets/architecture_followup_refactor/P01_shell_composition_root_collapse_WRAPUP.md`

## Required Behavior

- Make `composition.py` the only packet-owned composition root and context-property authority for shell startup.
- Move packet-owned non-lifecycle shell assembly and pass-through behavior out of `ShellWindow`.
- Keep `ShellWindow` responsible for top-level Qt ownership, widget lifecycle, and final event wiring only.
- Update inherited shell bootstrap and runtime regression anchors in place when public packet-owned host attachment seams change.

## Non-Goals

- No workspace-library or project-session facade cleanup yet; that belongs to `P02`.
- No graph, persistence, runtime, or viewer authority work yet.
- No new user-facing shell features.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_followup_refactor/P01_shell_composition_root_collapse_WRAPUP.md`

## Acceptance Criteria

- `composition.py` is the sole packet-owned shell composition root.
- `ShellWindow` is no longer the packet-owned shell application-command hub.
- The inherited shell bootstrap and runtime regression anchors pass.

## Handoff Notes

- `P02` narrows the remaining controller and service entry surfaces against this slimmer host.
