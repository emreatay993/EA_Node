# PORT_LABEL_VISIBILITY P01: Preferences + Bridge Contract

## Objective
- Add the additive `graphics.canvas.show_port_labels` schema plus the shell/canvas getter-setter surfaces that later packets will reuse from the View menu, Graphics Settings, and QML host bindings.

## Preconditions
- `P00` is marked `PASS` in [PORT_LABEL_VISIBILITY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_STATUS.md).
- No later `PORT_LABEL_VISIBILITY` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/main_window_shell/bridge_contracts.py`

## Conservative Write Scope
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/main_window_shell/bridge_contracts.py`
- `docs/specs/work_packets/port_label_visibility/P01_preferences_bridge_contract_WRAPUP.md`

## Required Behavior
- Add `graphics.canvas.show_port_labels` to the app-wide graphics preferences schema with a normalized boolean default of `true`.
- Keep the app-preferences document version at `2`; treat this as an additive schema extension rather than a breaking migration.
- Thread the resolved value through the shell workspace UI state and the QML-facing canvas bridge surfaces that already publish graphics preferences.
- Expose a stable runtime getter property named `graphics_show_port_labels` and a persistent setter/update path named `set_graphics_show_port_labels(bool)` on the host/canvas surface so later packets can call it without inventing a parallel preference mutation path.
- Preserve all existing graphics preference fields, theme behavior, and visible canvas/node behavior in this packet.
- Add or update tests that lock the additive schema round-trip, bridge/runtime exposure, and persistent setter behavior.

## Non-Goals
- No View-menu action or Graphics Settings dialog control yet. `P02` owns those UI surfaces.
- No scene metric or width-policy changes yet. `P03` owns those.
- No QML label-hide or tooltip-only behavior yet. `P04` owns the presentation rollout.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_graphics_settings_preferences.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/bridge_contracts.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_graphics_settings_preferences.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/port_label_visibility/P01_preferences_bridge_contract_WRAPUP.md`

## Acceptance Criteria
- The additive preference schema round-trips with `show_port_labels=True` as the default and a persisted `False` alternative.
- Shell/canvas bridge surfaces expose `graphics_show_port_labels` without breaking existing graphics-preference contracts.
- A persistent host setter path exists for later packets to call without reopening the preferences plumbing.
- No user-facing View-menu, Graphics Settings, width-policy, or QML label-visibility changes are intentionally introduced in this packet.

## Handoff Notes
- Record the exact getter/setter/property names in the wrap-up so `P02` and `P04` reuse them verbatim.
- If the host setter path reuses an existing app-preferences update helper, note that explicitly so later packets do not add a second persistence branch.
