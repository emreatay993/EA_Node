# Architecture Requirements

## Scope
- `REQ-ARCH-001`: The app shall be Windows-first (Windows 10/11) and implemented in Python + PyQt6.
- `REQ-ARCH-002`: The graph editor UI shall use `QGraphicsScene/QGraphicsView` with custom `QGraphicsItem` nodes/edges.
- `REQ-ARCH-003`: The runtime shall use hybrid DAG + event trigger execution semantics.
- `REQ-ARCH-004`: Workflow execution shall run in a dedicated worker process per run session.

## Public Interfaces
- `REQ-ARCH-005`: Main window shall expose:
  - `set_engine_state(state, details='')`
  - `set_job_counts(running, queued, done, failed)`
  - `set_metrics(cpu_percent, ram_used_gb, ram_total_gb)`
  - `set_notification_counts(warnings, errors)`
- `REQ-ARCH-006`: Workspace manager shall expose create/rename/duplicate/close/switch workspace and create/switch view APIs.
- `REQ-ARCH-007`: Node SDK shall define typed node specs (`NodeTypeSpec`, `PortSpec`, `PropertySpec`) and executable plugin contract.
- `REQ-ARCH-008`: Persistence shall expose load/save/migrate API for `.sfe` files.
- `REQ-ARCH-009`: Main window shall expose orchestration UI APIs `open_workflow_settings()` and `toggle_script_editor()`.

## Acceptance
- `AC-REQ-ARCH-001-01`: Application launches on Windows with PyQt6 and displays the main shell.
- `AC-REQ-ARCH-004-01`: Run starts without blocking UI thread; worker failure does not crash UI process.
- `AC-REQ-ARCH-005-01`: Status bar methods update widgets in real time.
