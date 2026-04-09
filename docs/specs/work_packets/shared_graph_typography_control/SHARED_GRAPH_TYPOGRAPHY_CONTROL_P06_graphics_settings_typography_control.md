# SHARED_GRAPH_TYPOGRAPHY_CONTROL P06: Graphics Settings Typography Control

## Objective
- Add the user-facing Graphics Settings `Theme` > `Typography` control for `graph_label_pixel_size` and prove end-user preference round-trip against the retained dialog, shell, and QML preference seams.

## Preconditions
- `P05` is marked `PASS` in [SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md](./SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md).
- No later `SHARED_GRAPH_TYPOGRAPHY_CONTROL` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`
- `docs/specs/work_packets/shared_graph_typography_control/P06_graphics_settings_typography_control_WRAPUP.md`

## Required Behavior
- Add a `Typography` card on the Graphics Settings `Theme` page with one `QSpinBox` that exposes `graph_label_pixel_size` and clamps the UI range to `8..18`.
- Ensure the dialog presents the packet-owned default value `10` when the incoming settings payload is missing or requires normalization of the `graphics.typography` block.
- Wire the control through `set_values()` and `values()` so the dialog round-trips `graphics.typography.graph_label_pixel_size` without disturbing existing theme or graph-theme controls.
- Keep the new control app-global and preference-backed; do not add a graph-theme-specific typography editor or a session-only override path.
- Reuse the already-landed preference, shell, bridge, and QML role contract from `P01` through `P05` instead of adding a second dialog-local typography state.
- Add packet-owned regression tests whose names include `graph_typography_dialog` so the targeted verification commands below remain stable.

## Non-Goals
- No new shared typography roles or consumer-local typography math.
- No requirement, QA-matrix, or traceability refresh yet.
- No passive-style schema or dialog changes.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_dialog.py tests/test_graphics_settings_preferences.py -k graph_typography_dialog --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py tests/graph_track_b/qml_preference_bindings.py -k graph_typography_dialog --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_dialog.py -k graph_typography_dialog --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/shared_graph_typography_control/P06_graphics_settings_typography_control_WRAPUP.md`

## Acceptance Criteria
- The Graphics Settings `Theme` page exposes one `Typography` control backed by a `QSpinBox` in the inclusive `8..18` range.
- The dialog presents the packet-owned default value when the typography preference is absent or invalid.
- Dialog `set_values()` and `values()` round-trip `graphics.typography.graph_label_pixel_size`.
- The packet-owned `graph_typography_dialog` regressions prove the user-facing control, persisted preference behavior, and live QML preference handoff.

## Handoff Notes
- `P07` publishes the retained QA matrix and traceability evidence for the full feature using the proof surface established here and in `P01` through `P05`.
- Any later packet that changes the user-facing control location, control type, or end-user round-trip contract must inherit and update `tests/test_graphics_settings_dialog.py`, `tests/test_graphics_settings_preferences.py`, `tests/main_window_shell/shell_basics_and_search.py`, and `tests/graph_track_b/qml_preference_bindings.py`.
