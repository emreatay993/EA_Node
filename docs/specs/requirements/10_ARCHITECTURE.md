# Architecture Requirements

## Scope
- `REQ-ARCH-001`: The app shall be Windows-first (Windows 10/11) and implemented in Python + PyQt6.
- `REQ-ARCH-002`: The graph editor UI shall use a QML (`QtQuick`) canvas with bridge-first Python shell/canvas context properties for nodes, edges, selection, camera state, and shell-owned canvas commands.
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
- `REQ-ARCH-006`: `WorkspaceManager` shall be the public authority for create/rename/duplicate/close/switch workspace and create/switch view APIs.
- `REQ-ARCH-007`: Node SDK shall define typed node specs (`NodeTypeSpec`, `PortSpec`, `PropertySpec`) and executable plugin contract.
- `REQ-ARCH-008`: Persistence shall expose load/save/migrate API for `.sfe` files, with split internals for project codec, migration/normalization, and session/autosave storage services.
- `REQ-ARCH-009`: `ShellWindow` shall expose orchestration UI APIs `show_workflow_settings_dialog()` and `set_script_editor_panel_visible()`.
- `REQ-ARCH-012`: app-wide graphics preferences shall be exposed through a dedicated preferences controller/store and consumed by both QWidget and QML shell surfaces without breaking existing shell/graph canvas integration contracts.
- `REQ-ARCH-013`: graph node/edge theming shall use a dedicated graph-theme pipeline (`ea_node_editor/ui/graph_theme/*` + `graphThemeBridge`) that remains separate from shell/canvas chrome theming in `ea_node_editor/ui/theme/*` + `ThemeBridge`.
- `REQ-ARCH-014`: project persistence architecture shall keep `.sfe` as the canonical project document while project-managed files live in a sibling `<project-stem>.data/` sidecar with `assets/`, `artifacts/`, and `.staging/` scratch storage rather than a second project document format.
- `REQ-ARCH-015`: managed-file state shall remain additive under `metadata.artifact_store`, using `artifact://<artifact_id>` and `artifact-stage://<artifact_id>` strings plus a shared resolver/store seam that serves persistence, preview, and execution flows without introducing a full artifact-manager subsystem.
- `REQ-ARCH-016`: the cross-process viewer subsystem shall remain registry-driven: execution-side viewer backends publish `backend_id`, typed `transport` descriptors, `transport_revision`, and explicit live-open status or blocker fields through `ViewerSessionService`, while shell-owned `ViewerSessionBridge`, `ViewerHostService`, `ViewerWidgetBinderRegistry`, and `EmbeddedViewerOverlayManager` host backend widgets without moving raw DPF, PyVista, or VTK objects into ordinary graph payloads or the UI protocol.

## Acceptance
- `AC-REQ-ARCH-001-01`: Application launches on Windows with PyQt6 and displays the main shell.
- `AC-REQ-ARCH-002-01`: Main shell loads `GraphCanvas` composition modules, retains editing overlays (grid, edge layer, minimap, context menus, marquee/pan inputs), and exports the split shell/canvas bridge context without reintroducing raw `mainWindow` / `sceneBridge` / `viewBridge` globals.
- `AC-REQ-ARCH-004-01`: Run starts without blocking UI thread; worker failure does not crash UI process.
- `AC-REQ-ARCH-005-01`: Status methods update QML shell status surfaces in real time through bridge models.
- `AC-REQ-ARCH-011-01`: Library drop, minimap toggle, and canvas hit-testing continue to invoke the `GraphCanvas` integration contract methods without runtime errors.
- `AC-REQ-ARCH-012-01`: graphics preference updates reapply shell/chrome theme state and runtime graphics flags without breaking `GraphCanvas` integration contracts.
- `AC-REQ-ARCH-013-01`: `NodeCard` and `EdgeLayer` consume `graphThemeBridge` tokens independently from shell/canvas chrome surfaces that stay on `ThemeBridge`.
- `AC-REQ-ARCH-014-01`: managed-file save/open/recovery regressions preserve the `.sfe` plus sibling `.data` split and keep project-managed files out of a schema-version bump.
- `AC-REQ-ARCH-015-01`: managed preview, runtime artifact-ref, and stored-output regressions resolve `artifact://...` and `artifact-stage://...` values through the shared resolver/store seam, and `docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md` remains the published proof audit.
- `AC-REQ-ARCH-016-01`: execution-protocol, materialization, host-service, binder, and bridge regressions confirm worker-side DPF authority, registry-driven backend and binder seams, shell-owned widget hosting, and `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md` remains the published closeout audit.
