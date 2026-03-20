# GRAPHICS_PERFORMANCE_MODES P01: Preferences + Runtime Contract

## Objective
- Add the additive graphics-performance mode schema plus the runtime getter/setter surfaces that later packets will reuse from Graphics Settings, the status strip, and QML canvas bindings.

## Preconditions
- `P00` is marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- targeted graphics-preference and bridge/runtime contract tests

## Conservative Write Scope
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/main_window_shell/bridge_contracts.py`
- `docs/specs/work_packets/graphics_performance_modes/P01_preferences_runtime_contract_WRAPUP.md`

## Required Behavior
- Add `graphics.performance.mode` to the app-wide graphics preferences schema with normalized enum values `full_fidelity` and `max_performance`.
- Keep the app-preferences document version at `2`; treat this as an additive schema extension rather than a breaking migration.
- Thread the resolved mode through the runtime graphics application path, including the shell workspace UI state and the QML-facing bridge surfaces that already publish graphics preferences.
- Expose one stable runtime getter property and one persistent setter/update path that later packets can call from Graphics Settings and the status-strip toggle.
- Preserve all existing graphics preference fields, shell/theme behavior, and current canvas visuals in this packet.
- Add or update tests that lock the additive schema round-trip, window/bridge property exposure, and runtime preference propagation.

## Non-Goals
- No Graphics Settings dialog UI changes yet. `P02` owns that.
- No status-strip toggle yet. `P03` owns that.
- No canvas-performance behavior changes yet. `P04` and `P05` own those.
- No Node SDK or plugin contract changes yet. `P06` owns that.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_graphics_settings_preferences.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/bridge_contracts.py --ignore=venv -k "graphics" -q`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P01_preferences_runtime_contract_WRAPUP.md`

## Acceptance Criteria
- The additive preference schema round-trips with `full_fidelity` as the default and `max_performance` as a normalized persisted alternative.
- QML/runtime bridge surfaces expose the resolved mode without breaking existing graphics-preference contracts.
- A persistent setter/update path exists for later packets to call without reopening the preferences plumbing.
- No user-visible shell/canvas behavior changes are intentionally introduced in this packet.

## Handoff Notes
- Record the final getter/setter names in the wrap-up so `P02` and `P03` reuse them instead of inventing parallel preference mutation paths.
- If any bridge alias path had to be updated, note the narrow compatibility boundary explicitly in residual risks.
