# ARCH_SIXTH_PASS P01: Shell Bootstrap Contract

## Objective
- Replace the reflective shell bootstrap bundle flow with an explicit shell composition contract so startup wiring is typed, reviewable, and no longer acts like a service locator.

## Preconditions
- `P00` is marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- shell composition root
- shell bootstrap sequencing
- startup and shell bootstrap regression coverage

## Conservative Write Scope
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/app.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/arch_sixth_pass/P01_shell_bootstrap_contract_WRAPUP.md`

## Required Behavior
- Split `composition.py` into an explicit dependency factory and bootstrap coordinator instead of one large reflective assembler.
- Remove or sharply reduce reflective host mutation patterns such as generic bundle application for packet-owned shell bootstrap paths.
- Keep startup entry behavior, session restore order, timer setup, QML load order, and shell object ownership stable.
- Preserve the current source launch and installed bootstrap path behavior.

## Non-Goals
- No presenter split in this packet.
- No QML bridge contract removal in this packet.
- No runtime snapshot, plugin, or persistence boundary changes in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py -q -k "MainWindowShellBootstrapCompositionTests or MainWindowShellContextBootstrapTests"`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P01_shell_bootstrap_contract_WRAPUP.md`

## Acceptance Criteria
- Shell bootstrap wiring no longer depends on a broad reflective bundle-application step for packet-owned paths.
- Startup and shell bootstrap tests pass with no user-visible startup regressions.
- `ShellWindow` bootstrap dependencies are clearer and more explicit than the current composition-root pattern.

## Handoff Notes
- `P02` owns `ShellWindow` facade reduction and presenter surface cleanup.
- Keep packet-owned changes focused on bootstrap and composition boundaries only.
