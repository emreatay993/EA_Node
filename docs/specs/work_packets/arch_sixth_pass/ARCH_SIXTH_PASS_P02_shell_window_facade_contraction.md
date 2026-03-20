# ARCH_SIXTH_PASS P02: ShellWindow Facade Contraction

## Objective
- Reduce `ShellWindow` and the shell presenter layer to a real host facade that owns Qt lifecycle and packet-owned public slots, not broad business logic and compatibility passthroughs.

## Preconditions
- `P00` and `P01` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ShellWindow` host surface
- shell presenters
- packet-owned shell dialogs and slot owners

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/*.py`
- `ea_node_editor/ui/shell/controllers/*.py`
- `tests/test_main_window_shell.py`
- `tests/test_window_library_inspector.py`
- `tests/test_graphics_settings_dialog.py`
- `docs/specs/work_packets/arch_sixth_pass/P02_shell_window_facade_contraction_WRAPUP.md`

## Required Behavior
- Move packet-owned nontrivial shell logic out of `ShellWindow` into focused presenter, flow, or controller helpers.
- Split `presenters.py` when packet-owned seams can be made explicit without behavior changes.
- Leave `ShellWindow` responsible for Qt host lifecycle, signal exposure, dialog launching, and stable public host slots only.
- Preserve current QML-facing behavior, QAction wiring, and inspector/library/runtime flows exactly.

## Non-Goals
- No bridge contract removal in this packet.
- No graph authoring transaction changes in this packet.
- No verification-runner or docs-only work in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_window_library_inspector.py tests/test_graphics_settings_dialog.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py -q -k "MainWindowShellTelemetryTests or MainWindowShellHostProtocolStateTests"`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P02_shell_window_facade_contraction_WRAPUP.md`

## Acceptance Criteria
- `ShellWindow` owns materially less nontrivial shell business logic than the current baseline.
- Packet-owned presenter surfaces are more focused and easier to review than the current monolithic presenter module.
- Verification passes with no QML-facing or shell interaction regressions.

## Handoff Notes
- `P03` owns shell bridge and controller contract hardening after the facade surface is smaller.
- Preserve stable public slot and property names unless `P03` explicitly migrates a packet-owned contract.
