# Architecture Requirements

## Scope
- `REQ-ARCH-001`: The app shall be Windows-first (Windows 10/11) and implemented in Python + PyQt6.
- `REQ-ARCH-002`: The graph editor UI shall use a QML (`QtQuick`) canvas as a QML-shell client of the Corex kernel, with bridge-first Python shell/canvas context properties for nodes, edges, selection, camera state, and shell-owned canvas commands.
- `REQ-ARCH-010`: `GraphCanvas.qml` shall remain an orchestration surface that composes modular canvas components (`GraphCanvasBackground`, `GraphCanvasDropPreview`, `GraphCanvasMinimapOverlay`, `GraphCanvasInputLayers`, `GraphCanvasContextMenus`) plus `GraphCanvasLogic.js`.
- `REQ-ARCH-011`: Graph canvas integration contract methods (`toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, `performLibraryDrop()`) shall remain available to shell/drop workflows.
- `REQ-ARCH-003`: The runtime shall use hybrid DAG + event trigger execution semantics.
- `REQ-ARCH-004`: Workflow execution shall run in a dedicated worker process per run session. Secure remote execution is a separate planned scope under `REQ-EXEC-020` and `REQ-INT-018`; it does not widen this requirement or its existing proof.
- `REQ-ARCH-017`: Corex is pre-release, so architecture cleanup may intentionally break old `.cxproj`, plugin, QML, action, and Python import compatibility when removing those compatibility seams reduces ambiguity around the canonical architecture.
- `REQ-ARCH-018`: The documented modernization direction shall be Option B: a GUI-independent headless Corex kernel with explicit extension contracts, with the QML shell treated as one client rather than the owner of kernel behavior. Permissioned agent orchestration is a separate planned client and policy layer under `REQ-ARCH-020`, `REQ-EXEC-022`, and `REQ-UI-058`; it does not widen this requirement or its existing proof.
- `REQ-ARCH-019`: Strict current-schema persistence, canonical action IDs, explicit surface/input contracts, headless execution APIs, and runtime backend, toolchain, and artifact descriptors shall be treated as planned public interfaces for later modernization packets. The workflow-interface, durable-snapshot, remote-execution, and permissioned-agent contracts are specified separately by `REQ-NODE-036`, `REQ-EXEC-017`, `REQ-PERSIST-026`, `REQ-EXEC-020`, and `REQ-ARCH-020`; this dependency pointer does not claim those contracts are implemented.
- `REQ-ARCH-020`: Permissioned agent orchestration shall be a planned client of the headless Corex kernel that can propose typed plans and tool calls only through public graph, execution, persistence, and integration authorities; shall apply explicit capability grants, user-approval policy, cancellation, and immutable provenance to each operation; and shall prohibit direct model writes, hidden external side effects, or privilege escalation. Implementation shall remain blocked until `REQ-NODE-036`, `REQ-EXEC-017`, `REQ-EXEC-018`, `REQ-EXEC-020`, and `REQ-PERSIST-026` are accepted. Evidence crosswalk: `SYN-OPP-0008`.

## Public Interfaces
- `REQ-ARCH-005`: `ShellWindow` shall expose:
  - `update_engine_status(state, details='')`
  - `update_job_counters(running, queued, done, failed)`
  - `update_system_metrics(cpu_percent, ram_used_gb, ram_total_gb)`
  - `update_notification_counters(warnings, errors)`
- `REQ-ARCH-006`: `WorkspaceManager` shall be the public authority for create/rename/duplicate/close/switch workspace and create/switch view APIs.
- `REQ-ARCH-007`: Node SDK shall define typed node specs (`NodeTypeSpec`, `PortSpec`, `PropertySpec`) and executable plugin contract.
- `REQ-ARCH-008`: Persistence shall expose load/save/current-schema-normalization APIs for `.cxproj` files, with split internals for project codec, schema validation, normalization, and session/autosave storage services.
- `REQ-ARCH-009`: `ShellWindow` shall expose orchestration UI APIs `show_workflow_settings_dialog()` and `set_script_editor_panel_visible()`.
- `REQ-ARCH-012`: app-wide graphics preferences shall be exposed through a dedicated preferences controller/store and consumed by both QWidget and QML shell surfaces without breaking existing shell/graph canvas integration contracts.
- `REQ-ARCH-013`: graph node/edge theming shall use a dedicated graph-theme pipeline (`ea_node_editor/ui/graph_theme/*` + `graphThemeBridge`) that remains separate from shell/canvas chrome theming in `ea_node_editor/ui/theme/*` + `ThemeBridge`; the active graph palette is resolved from the active shell theme rather than a separate user selection.
- `REQ-ARCH-014`: project persistence architecture shall keep `.cxproj` as the canonical project document while project files live in a sibling `<project-stem>.data/workspaces/<workspace-folder>/nodes/<node-folder>/` sidecar with `in/`, `out/`, and `tmp/` node folders rather than a second project document format.
- `REQ-ARCH-015`: project-file state shall remain additive under `metadata.artifact_store`, using `saved://<artifact_id>` and `temp://<artifact_id>` strings plus a shared resolver/store seam that serves persistence, preview, and execution flows without introducing a full artifact-manager subsystem.
- `REQ-ARCH-016`: the cross-process viewer subsystem shall remain registry-driven: execution-side viewer backends publish `backend_id`, typed `transport` descriptors, `transport_revision`, and explicit live-open status or blocker fields through `ViewerSessionService`, while shell-owned `ViewerSessionBridge`, `ViewerHostService`, `ViewerWidgetBinderRegistry`, and `EmbeddedViewerOverlayManager` host backend widgets without moving raw PyVista, VTK, or other native scene objects into ordinary graph payloads or the UI protocol.

## Acceptance
- `AC-REQ-ARCH-001-01`: Application launches on Windows with PyQt6 and displays the main shell.
- `AC-REQ-ARCH-002-01`: Main shell loads `GraphCanvas` composition modules, retains editing overlays (grid, edge layer, minimap, context menus, marquee/pan inputs), and exports the split shell/canvas bridge context without reintroducing raw `mainWindow` / `sceneBridge` / `viewBridge` globals.
- `AC-REQ-ARCH-004-01`: Run starts without blocking UI thread; worker failure does not crash UI process.
- `AC-REQ-ARCH-005-01`: Status methods update QML shell status surfaces in real time through bridge models.
- `AC-REQ-ARCH-011-01`: Library drop, minimap toggle, and canvas hit-testing continue to invoke the `GraphCanvas` integration contract methods without runtime errors.
- `AC-REQ-ARCH-012-01`: graphics preference updates reapply shell/chrome theme state and runtime graphics flags without breaking `GraphCanvas` integration contracts.
- `AC-REQ-ARCH-013-01`: `NodeCard` and `EdgeLayer` consume `graphThemeBridge` tokens independently from shell/canvas chrome surfaces that stay on `ThemeBridge`.
- `AC-REQ-ARCH-014-01`: project-file save/open/recovery regressions preserve the `.cxproj` plus sibling `.data/workspaces` split and keep project files out of a schema-version bump.
- `AC-REQ-ARCH-015-01`: managed preview, runtime artifact-ref, and stored-output regressions resolve `saved://...` and `temp://...` values through the shared resolver/store seam, and `docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md` remains the published proof audit.
- `AC-REQ-ARCH-016-01`: execution-protocol, engineering-backend, host-service, binder, and bridge regressions confirm worker-side scene authority, registry-driven backend and binder seams, shell-owned widget hosting, and `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md` remains the published closeout audit.
- `AC-REQ-ARCH-020-01`: Architecture and adversarial-boundary tests shall confirm agent operations enter through public authorities, every operation resolves an explicit grant and approval decision, cancellation and provenance survive client handoff, direct model writes and hidden side effects are rejected, and orchestration remains unavailable while any declared prerequisite requirement is unaccepted.
