# Architecture Requirements

## Scope
- `REQ-ARCH-001`: The app shall be Windows-first (Windows 10/11) and implemented in Python + PyQt6.
- `REQ-ARCH-002`: The graph editor UI shall use a QML (`QtQuick`) canvas with Python bridge/controller models for nodes, edges, selection, and camera state.
- `REQ-ARCH-010`: `GraphCanvas.qml` shall remain an orchestration surface that composes modular canvas components (`GraphCanvasBackground`, `GraphCanvasDropPreview`, `GraphCanvasMinimapOverlay`, `GraphCanvasInputLayers`, `GraphCanvasContextMenus`) plus `GraphCanvasLogic.js`.
- `REQ-ARCH-011`: Graph canvas integration contract methods (`toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, `performLibraryDrop()`) shall remain available to shell/drop workflows.
- `REQ-ARCH-003`: The runtime shall use hybrid DAG + event trigger execution semantics.
- `REQ-ARCH-004`: Workflow execution shall run in a dedicated worker process per run session.

## Public Interfaces
- `REQ-ARCH-005`: `ShellWindow` shall expose:
  - `update_engine_status(state, details='')`
  - `update_job_counters(running, queued, done, failed)`
  - `update_system_metrics(cpu_percent, ram_used_gb, ram_total_gb)`
  - `update_notification_counters(warnings, errors)`
- `REQ-ARCH-006`: Workspace manager shall expose create/rename/duplicate/close/switch workspace and create/switch view APIs.
- `REQ-ARCH-007`: Node SDK shall define typed node specs (`NodeTypeSpec`, `PortSpec`, `PropertySpec`) and executable plugin contract.
- `REQ-ARCH-008`: Persistence shall expose load/save/migrate API for `.sfe` files, with split internals for project codec, migration/normalization, and session/autosave storage services.
- `REQ-ARCH-009`: `ShellWindow` shall expose orchestration UI APIs `show_workflow_settings_dialog()` and `set_script_editor_panel_visible()`.

## Acceptance
- `AC-REQ-ARCH-001-01`: Application launches on Windows with PyQt6 and displays the main shell.
- `AC-REQ-ARCH-002-01`: Main shell loads `GraphCanvas` composition modules and retains editing overlays (grid, edge layer, minimap, context menus, marquee/pan inputs).
- `AC-REQ-ARCH-004-01`: Run starts without blocking UI thread; worker failure does not crash UI process.
- `AC-REQ-ARCH-005-01`: Status methods update QML shell status surfaces in real time through bridge models.
- `AC-REQ-ARCH-011-01`: Library drop, minimap toggle, and canvas hit-testing continue to invoke the `GraphCanvas` integration contract methods without runtime errors.
