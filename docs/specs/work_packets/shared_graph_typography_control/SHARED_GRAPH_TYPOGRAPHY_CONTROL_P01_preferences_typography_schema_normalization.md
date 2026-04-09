# SHARED_GRAPH_TYPOGRAPHY_CONTROL P01: Preferences Typography Schema Normalization

## Objective
- Add the persisted `graphics.typography.graph_label_pixel_size` default and normalization contract so later shell, QML, and dialog packets consume one stable app-preference source of truth.

## Preconditions
- `P00` is marked `PASS` in [SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md](./SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md).
- No later `SHARED_GRAPH_TYPOGRAPHY_CONTROL` packet is in progress.

## Execution Dependencies
- `P00`

## Target Subsystems
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `tests/test_graphics_settings_preferences.py`

## Conservative Write Scope
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `tests/test_graphics_settings_preferences.py`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`
- `docs/specs/work_packets/shared_graph_typography_control/P01_preferences_typography_schema_normalization_WRAPUP.md`

## Required Behavior
- Extend `DEFAULT_GRAPHICS_SETTINGS` with the packet-owned `typography.graph_label_pixel_size` field under `graphics`.
- Keep the default value at `10`.
- Normalize missing, non-integer, low, and high values in `normalize_graphics_settings()` to an integer inside the inclusive `8..18` range.
- Preserve backward compatibility for older preference payloads that lack a `typography` block or contain unrelated graphics settings only.
- Preserve load/save of the nested `graphics.typography` block instead of flattening the packet-owned key into an ad hoc side path.
- Ensure the normalized typography value reaches the existing host-application graphics-preference apply path so the host receives the resolved size that later shell/QML packets project.
- Keep the packet-owned preference additive and app-global; do not add graph-theme-scoped typography storage or `.sfe` persistence fields.
- Add packet-owned regression tests whose names include `graph_typography_preferences` so the targeted verification commands below remain stable.

## Non-Goals
- No shell/workspace/window/bridge/QML changes yet.
- No geometry or text-width metric changes yet.
- No Graphics Settings dialog control yet.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py -k graph_typography_preferences --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py -k graph_typography_preferences --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/shared_graph_typography_control/P01_preferences_typography_schema_normalization_WRAPUP.md`

## Acceptance Criteria
- `graphics.typography.graph_label_pixel_size` is part of the normalized graphics-settings schema with default `10`.
- Invalid persisted values clamp back into the packet-owned `8..18` range without disturbing unrelated graphics preferences.
- Preferences persistence/load round-trips the nested `graphics.typography` block, and the host-application graphics apply path receives the normalized size.
- The packet-owned `graph_typography_preferences` regressions pass and prove the schema/default/normalization behavior.

## Handoff Notes
- `P02` consumes the normalized typography value on the workspace/window/bridge path. Do not rename the `graphics.typography.graph_label_pixel_size` key after this packet.
- Any later packet that changes the normalization range or default must inherit and update `tests/test_graphics_settings_preferences.py`.
