# RC3 P09 - QML Shell + Graph Cutover

## Status
- Completed (single cutover)

## Scope Decisions
- Runtime shell is now QML-first (`ea_node_editor/ui_qml/MainShell.qml`) hosted by `QQuickWidget`.
- Runtime graph canvas is QML (`ea_node_editor/ui_qml/components/GraphCanvas.qml`) driven by Python bridge models.
- QWidget/QGraphics runtime path is removed from `ShellWindow`; legacy graph scene/view/items modules are fully removed.
- No Option-2 fallback path was introduced for startup/runtime cutover.

## Locked Compatibility
- `.sfe` serialization schema behavior is unchanged.
- Execution engine process model and event handling are unchanged.
- Node SDK contracts (`NodeTypeSpec`, `PortSpec`, `PropertySpec`, plugin execution contract) are unchanged.
- `ShellWindow` public shell APIs remain:
  - `update_engine_status(state, details='')`
  - `update_job_counters(running, queued, done, failed)`
  - `update_system_metrics(cpu_percent, ram_used_gb, ram_total_gb)`
  - `update_notification_counters(warnings, errors)`
  - `show_workflow_settings_dialog()`
  - `set_script_editor_panel_visible()`

## Visual Source of Truth
- Stitch references used from `docs/specs/gui/*.zip` (`code.html` + `screen.png`).
- QML structure mirrors the expected shell zones: left library, center graph + workspace tabs + console, right inspector, status strip.

## Startup + Packaging
- `ea_node_editor/app.py` now forces software QtQuick backend defaults for headless/offscreen stability.
- `main.py` now exposes `main()` entrypoint wrapper.
- `ea_node_editor.spec` now includes QML resources and QtQuick hidden imports.

## Test Updates
- UI parity tests were migrated to QML-era bridge assertions:
  - `tests/test_main_window_shell.py`
  - `tests/test_script_editor_dock_rc2.py`
  - `tests/test_theme_shell_rc2.py`
