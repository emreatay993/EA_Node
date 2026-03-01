# RC3 P09 - QML Shell + Graph Cutover

## Status
- Completed (single cutover)

## Scope Decisions
- Runtime shell is now QML-first (`ea_node_editor/ui_qml/MainShell.qml`) hosted by `QQuickWidget`.
- Runtime graph canvas is QML (`ea_node_editor/ui_qml/components/GraphCanvas.qml`) driven by Python bridge models.
- QWidget/QGraphics runtime path is removed from `MainWindow`; legacy graph modules remain only for non-runtime compatibility tests.
- No Option-2 fallback path was introduced for startup/runtime cutover.

## Locked Compatibility
- `.sfe` serialization schema behavior is unchanged.
- Execution engine process model and event handling are unchanged.
- Node SDK contracts (`NodeTypeSpec`, `PortSpec`, `PropertySpec`, plugin execution contract) are unchanged.
- Main window public shell APIs remain:
  - `set_engine_state(state, details='')`
  - `set_job_counts(running, queued, done, failed)`
  - `set_metrics(cpu_percent, ram_used_gb, ram_total_gb)`
  - `set_notification_counts(warnings, errors)`
  - `open_workflow_settings()`
  - `toggle_script_editor()`

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
