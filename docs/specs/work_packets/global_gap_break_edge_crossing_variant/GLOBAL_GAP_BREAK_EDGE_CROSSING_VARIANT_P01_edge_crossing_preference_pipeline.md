# GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT P01: Edge Crossing Preference Pipeline

## Objective

- Add the global `edge_crossing_style` preference, surface it in graphics settings, and wire it through the shell and QML canvas stack so the renderer can consume it in a later packet without changing edge geometry or persistence behavior yet.

## Preconditions

- `P00` is complete and the packet set is registered in `.gitignore` and `docs/specs/INDEX.md`.
- The implementation base is current `main`.

## Execution Dependencies

- `GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P00_bootstrap.md`

## Target Subsystems

- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/main_window_shell/shell_basics_and_search.py`

## Conservative Write Scope

- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `docs/specs/work_packets/global_gap_break_edge_crossing_variant/P01_edge_crossing_preference_pipeline_WRAPUP.md`
- `docs/specs/work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md`

## Required Behavior

- Add `graphics.canvas.edge_crossing_style` as a normalized application preference with allowed values `none` and `gap_break`.
- Keep the default value at `none`.
- Surface the preference in the Graphics Settings canvas/visual page as a `Crossing style` control with `None` and `Gap break` options and round-trip load/save coverage.
- Expose the effective value through the shell presenter/window path as `graphics_edge_crossing_style` so QML can bind it without reaching back into settings directly.
- Add or extend the canvas state bridge exposure so `GraphCanvas.qml` receives `edgeCrossingStyle` and forwards it to `EdgeLayer.qml` as `edgeCrossingStyle`.
- Keep `EdgeLayer.qml` behavior unchanged apart from accepting the property and remaining ready for `P02`.
- Preserve existing `.sfe` persistence behavior; do not add per-edge state or serialization fields.
- Add targeted regression coverage for settings normalization, dialog persistence, QML preference binding, and shell exposure.

## Non-Goals

- No crossing-decoration math or segmented under-edge rendering yet.
- No changes to hit testing, label anchors, culling, routing, or arrowhead placement.
- No requirements-doc, QA-matrix, or traceability updates in this packet.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py tests/graph_track_b/qml_preference_bindings.py tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py --ignore=venv -q
```

## Expected Artifacts

- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `docs/specs/work_packets/global_gap_break_edge_crossing_variant/P01_edge_crossing_preference_pipeline_WRAPUP.md`

## Acceptance Criteria

- The new preference is available through the settings/preferences layer and normalizes invalid input back to `none`.
- The Graphics Settings canvas/visual page can display and persist the `Crossing style` control with `None` and `Gap break`.
- The `graphics_edge_crossing_style` property chain reaches `GraphCanvas.edgeCrossingStyle` and `EdgeLayer.edgeCrossingStyle` without introducing renderer behavior changes yet.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P01`. Do not start `P02` in the same thread.
- `P02` inherits this packet's exposed `edgeCrossingStyle` property and expands only the renderer behavior on top of it.
