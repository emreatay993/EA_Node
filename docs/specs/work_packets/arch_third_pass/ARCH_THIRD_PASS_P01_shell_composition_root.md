# ARCH_THIRD_PASS P01: Shell Composition Root

## Objective
- Turn `ea_node_editor/ui/shell/window.py` into a thinner facade by extracting constructor/bootstrap wiring, service assembly, and timer/setup orchestration into explicit composition helpers while keeping public `@pyqtSlot`, `@pyqtProperty`, and signal contracts stable.

## Preconditions
- `P00` is marked `PASS` in [ARCH_THIRD_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_STATUS.md).
- No later `ARCH_THIRD_PASS` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/app.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- packet-owned shell bootstrap modules under `ea_node_editor/ui/shell/`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/app.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- packet-owned shell bootstrap modules under `ea_node_editor/ui/shell/`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Extract constructor/bootstrap responsibilities from `ShellWindow.__init__` into explicit composition helpers or bootstrap modules instead of growing the host facade further.
- Move service assembly, context-bridge assembly, timer/setup orchestration, and related bootstrap wiring behind named helpers with clear ownership boundaries.
- Preserve the public `ShellWindow` slot/property/signal surface consumed by QML and tests.
- Keep current app startup, bridge registration, and offscreen-shell bootstrap behavior stable.
- Prefer packet-owned helper modules over adding new initialization complexity back into `window.py`.

## Non-Goals
- No workspace-library capability split yet; `P02` owns that.
- No root-QML bridge-first cleanup yet; `P03` owns that.
- No intentional workflow, persistence, or schema changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_bootstrap tests.test_main_window_shell -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_bootstrap -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_third_pass/P01_shell_composition_root_WRAPUP.md`

## Acceptance Criteria
- `window.py` delegates packet-owned bootstrap/composition work to explicit helpers instead of remaining the only owner of that setup logic.
- Public `ShellWindow` QML-facing slots, properties, and signals remain stable.
- Bootstrap and shell regression tests pass through the project venv.

## Handoff Notes
- `P02` owns the library/controller capability split; avoid widening this packet into workspace-library business logic refactors.
- Keep any new composition helpers narrow enough that later packets can reuse them without reopening startup wiring.
