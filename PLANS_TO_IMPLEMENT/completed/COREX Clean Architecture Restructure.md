# COREX Clean Architecture Restructure

## Summary

I would not do a greenfield rewrite. I would layer a new architecture program on top of the existing no-legacy cleanup contracts, preserving current `.sfe` behavior, launch paths, QML affordances, plugin descriptors, runtime snapshots, and viewer transport. The main goal is to break the current 14-domain import cycle into one-way layers with explicit service ports.

Target shape:

```text
ea_node_editor/
  bootstrap.py, app.py          # only composition roots
  domain/                       # pure project graph, workspace, node metadata
  contracts/                    # runtime, persistence, plugin, UI bridge DTOs
  application/                  # use cases/services/coordinators
  infrastructure/               # persistence, execution process, addons, artifacts
  presentation/
    shell/                      # PyQt host/controllers/presenters
    qml/                        # QML bridges/components
```

## Key Changes

- Make `bootstrap.py` and `app.py` the only full-object-graph wiring points. Everything below them imports inward or sideways only through contracts.
- Keep graph state pure: `ProjectData`, `WorkspaceData`, `NodeInstance`, `EdgeInstance`, and `ViewState` are passive domain data; semantic mutation goes through one validated mutation boundary.
- Split workspace responsibilities: `WorkspaceManager` owns workspace order/active tab state; `WorkspaceMutationService` owns view lifecycle and graph/view mutations.
- Move persistence to a narrow document boundary: serializer loads/saves current-schema project documents, artifact sidecars stay in `ProjectArtifactStore`, and viewer-session runtime state does not leak into project persistence.
- Make `runtime_contracts` truly contract-only. Move passive snapshot DTOs, runtime refs, and worker/viewer command-event schemas there; keep snapshot assembly, compiler, workers, cancellation, and viewer state machines in execution/application services.
- Keep `nodes` as SDK/descriptor/registry ownership; keep `addons` as enablement/hot-apply ownership. Put runtime rebuilds behind an application runtime coordinator instead of letting add-ons directly touch graph, workers, and viewers.
- Treat QML as ports/adapters: feature roots receive explicit ports; leaf QML stops reaching into `shellContext` or raw global bridge names.
- Promote viewer presentation into its own application service. `viewer_session_bridge.py`, `viewer_host_service.py`, overlays, fullscreen, preview temp files, and artifact resolution should be split into thin adapters over that service.
- Keep public surfaces small: `corex-node-editor`, `ea_node_editor.bootstrap:main`, `nodes/types`, `graph`, `runtime_contracts`, `ui.theme`, `ui.graph_theme`, and QML registration. Root scripts/devtools stay internal.

## Implementation Sequence

1. Add import-direction guardrails first: forbid `domain -> infrastructure/presentation`, `contracts -> execution/ui`, `nodes -> execution/ui`, `graph <-> persistence`, and `ui <-> ui_qml` cycles.
2. Extract contracts: runtime value codec, snapshot DTOs, command/event DTOs, plugin descriptors, and bridge payload types.
3. Clean graph/workspace mutation ownership: retire raw public graph mutators, centralize dirty marking, default-view repair, and active-view fallback.
4. Refactor persistence: separate authored document save/load, runtime unresolved envelope handling, artifact store/resolution, and session/autosave storage.
5. Split shell composition: keep `ShellWindow` thin, move `request_*` behavior into controllers/services, and retire `window_state/*` as behavior holders.
6. Restructure QML by feature roots: graph canvas, node chrome, viewer surfaces, passive media, fullscreen, overlays.
7. Extract cross-cutting services: settings/preferences, shell theme, graph theme, telemetry/status, project session I/O, viewer presentation.
8. Close with docs and public API cleanup: update `ARCHITECTURE.md`, remove stale `main.py` references, and document the new import rules.

## Test Plan

- Start every stage with `tests/test_context_budget_guardrails.py`, `tests/test_architecture_boundaries.py`, and `tests/test_run_verification.py`.
- Graph/workspace: mutation, Track-B, graph surface, comment backdrop, passive runtime wiring.
- Persistence/artifacts: serializer schema tests, artifact store/resolution, execution artifact refs.
- Runtime/viewer: worker protocol, viewer service, viewer bridge, fullscreen, overlay manager.
- Shell/QML: main window shell, graph action contracts, shell isolation, QML bridge contract tests.
- Final gate: `scripts/run_verification.py --mode full`, then manual Windows smoke for launch, project open/save, graph editing, runtime execution, viewer reopen/rerun, and artifact-backed content.

## Assumptions

- This is a behavior-preserving architecture rewrite, not a product redesign.
- Existing P00-P14 no-legacy cleanup contracts remain authoritative and are not reopened.
- Current `.sfe` files, descriptor-first plugins, runtime snapshots, and typed viewer transport remain canonical.
- Active uncommitted user work, especially comment popover and embedded viewer overlay work, is not overwritten or structurally moved without a separate migration packet.
