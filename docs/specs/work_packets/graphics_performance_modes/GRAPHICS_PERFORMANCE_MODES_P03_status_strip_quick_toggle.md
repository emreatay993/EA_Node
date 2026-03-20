# GRAPHICS_PERFORMANCE_MODES P03: Status Strip Quick Toggle

## Objective
- Add the persistent app-wide quick toggle for `Full Fidelity` / `Max Performance` in the shell status strip so users can switch modes without reopening Graphics Settings.

## Preconditions
- `P00` through `P02` are marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml`
- shell QML/bootstrap surfaces needed to route the existing persistent setter path into the status strip
- targeted shell runtime/QML regression tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `docs/specs/work_packets/graphics_performance_modes/P03_status_strip_quick_toggle_WRAPUP.md`

## Required Behavior
- Add a compact status-strip toggle that shows the current graphics performance mode and lets the user switch between the two locked mode values.
- Route the toggle through the persistent setter path from `P01` so using it immediately updates the saved app preference and stays in sync with Graphics Settings.
- Keep the status strip location app-global; do not add a toolbar control or canvas-corner control in this packet.
- Preserve the existing status-strip metrics/engine/notifications surfaces and keep the new control visually subordinate to them.
- Add or update focused shell runtime tests that lock the toggle’s presence, persistence behavior, and current-mode reflection.

## Non-Goals
- No automatic heuristics or auto-switching.
- No canvas-performance behavior changes yet. `P04` and `P05` own those.
- No new status-model abstraction unless the packet proves the existing shell bootstrap path is insufficient.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P03_status_strip_quick_toggle_WRAPUP.md`

## Acceptance Criteria
- The status strip exposes a global runtime toggle for `Full Fidelity` / `Max Performance`.
- Using the toggle updates the persisted app-wide preference immediately and stays in sync with the Graphics Settings modal.
- Existing shell status-strip contracts and status text surfaces remain operational.
- No toolbar/canvas-corner control or automatic switching logic is introduced in this packet.

## Handoff Notes
- Record the final object names and interaction path in the wrap-up so later packets can reuse them in tests and docs.
- Keep the toggle labels/copy aligned with `P02`; note any unavoidable wording divergence explicitly.
