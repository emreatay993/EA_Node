# Agent Map Coverage

This file records the current navigation owners for live source. Historical
implementation studies are intentionally excluded.

## Layer coverage

| Source area | Primary map | Main responsibility |
| --- | --- | --- |
| `ea_node_editor/graph` | [Graph Domain](subsystems/graph_domain.md) | Graph records, invariants, mutation, transforms, and workspace state |
| `ea_node_editor/execution` | [Execution](subsystems/execution.md) | Runtime snapshots, protocol, workers, and result transport |
| `ea_node_editor/persistence` | [Persistence](subsystems/persistence.md) | Project codecs, migrations, artifacts, and sessions |
| `ea_node_editor/nodes` | [Nodes And Built-ins](subsystems/nodes_registry_builtins.md) | Registry, contracts, built-ins, packages, and plugins |
| `ea_node_editor/ui` | [UI Shell](subsystems/ui_shell.md) | Shell composition, controllers, presenters, and native hosts |
| `ea_node_editor/ui_qml` | [QML Shell And Bridges](subsystems/qml_shell_and_bridges.md) | QML components, bridges, payloads, and graph surfaces |
| `ea_node_editor/runtime_contracts` | [Supporting Runtime Assets](subsystems/supporting_runtime_assets.md) | Data types, carriers, trees, intervals, and runtime references |
| `ea_node_editor/workspace` | [Workspace And Projects](subsystems/workspace_projects_session_library.md) | Workspace navigation, project sessions, and library state |
| `ea_node_editor/custom_workflows` | [Supporting Runtime Assets](subsystems/supporting_runtime_assets.md) | Reusable workflow storage and runtime support |
| `ea_node_editor/telemetry` | [Supporting Runtime Assets](subsystems/supporting_runtime_assets.md) | Telemetry and diagnostics |

## Cross-layer feature routes

- [Graph Scene Payload And Projection](feature_routes/graph_scene_payload_and_projection.md)
- [Graph Canvas Input Layers](feature_routes/graph_canvas_input_layers.md)
- [Edge Routing, Labels, And Progress](feature_routes/edge_routing_labels_progress.md)
- [Surface Input And Inline Controls](feature_routes/surface_input_and_inline_controls.md)
- [Port Availability And Default Values](feature_routes/port_availability_and_default_values.md)
- [Plotter Nodes](feature_routes/plotter_nodes.md)
- [Tabular Data Add-on And Preview](feature_routes/tabular_data_addon_preview.md)
- [MARS Solver Add-on](feature_routes/mars_solver_addon.md)
- [Neutral CAD/FE Engineering Viewer](feature_routes/neutral_cad_fe_engineering_viewer.md)
- [Ansys DPF Operator Viewer Transport](feature_routes/ansys_dpf_operator_viewer_transport.md)
- [Managed Artifacts And Project Data](feature_routes/managed_artifacts_project_data.md)
- [Project Session Files And Managed Artifacts](feature_routes/project_session_files_managed_artifacts.md)
- [Workspace Tabs, Library, And Context Menus](feature_routes/workspace_tabs_library_context_menus.md)
- [Core Integrations: File, Process, Email, Spreadsheet](feature_routes/core_integrations_file_process_email_spreadsheet.md)
- [SSH/SFTP Nodes](feature_routes/ssh_sftp_nodes.md)
- [Performance Harness And Graph Stress](feature_routes/performance_harness_graph_stress.md)
- [Retained Work-Packet QA Evidence And Spec Navigation](feature_routes/work_packet_docs_status_qa.md)

## Current ownership notes

- Incremental execution freshness, invalidation closure, settlement acceptance, and reset notifications are execution-owned. Shell/QML retain only bounded record-ID-selected presentation caches, exact node cleanup, and the transport-only current/expired projection.
- Viewer invalidation epochs are participant-local transport safety facts: prepared runs stage process/trusted/external snapshots plus an independent high-level/Bridge projection, worker preflight uses only the selected concrete view, and concrete responses translate to projection epochs only after local validation. Commit uses high-level active then child state-before-viewer locking, callback-free pinned delivery, all-or-none apply, and an irreversible gate-clearing finalizer. Failure remains byte-identical; only a state-free selected service may baseline-align its selected concrete workspace epoch. Project and generation replacement remain workspace-global.
- Tabular's seven executable declarations are owned by `addons/tabular_data/function_nodes.py`; dependency gating and bundle publication stay under the add-on catalog, while refs, preview, property editing, native preload, and execution helpers remain in their existing Tabular owners.
- MARS's three executable declarations are owned by `addons/mars/function_nodes.py`; its catalog owns dependency gating, package provenance, and bundle publication while `nodes.py` and `runtime.py` retain job construction, JSONL execution, cancellation, and artifact publication.
- Signal Plot declaration/execution is owned by `nodes/builtin_functions/plot_signal.py`,
  rendering by `execution/signal_plot_renderer.py`, and navigation by the plotter route.
- Declarative node controls are shared metadata-to-QML behavior owned by the
  node registry, graph-scene projection, and shared graph controls. Rendered
  list/group/control geometry belongs to Surface Input; payload and settings-band
  calculation belongs to Graph Scene Payload.
- Active-data wire behavior is owned jointly by graph mutation/history, graph-scene projection, graph-canvas input and action routing, and the retained/canvas edge renderers; passive-only and `flow` edges remain under their existing routes.
- Exact feature-map citations own QML components when present; the broader QML
  or graph-canvas subsystem remains the fallback only when no feature map cites
  that exact component path.
- Decorator-driven Python Script declarations are owned jointly by the node
  registry/parser, graph-owned atomic Apply, worker revalidation, and generic persistence.
- Deterministic `.cxpkg` schema-2 archive IO, static package validation, and
  immutable function-package asset provenance are owned by the Nodes map;
  title-icon projection remains owned by the icon and graph-scene routes.
- Open-session registry reload safety is shared by the graph compatibility checker,
  nodes candidate/package transaction, execution identity/admission guard, and the
  shell registry replacement coordinator; it is not a legacy compatibility layer.
- Novice plugin authoring is shared by the nodes-owned static/save backend, native
  PyQt dialog/editor, and shell controller/File actions; reload still routes only
  through the guarded registry replacement coordinator.
- The reserved built-in bundle owns exactly 68 inert function declarations under
  `nodes/builtin_functions/`; trusted helpers and data contracts remain under
  `nodes/builtins/`, and the current migration inventory pins 53 trusted
  exceptions while the 133-row pre-cutover catalog remains immutable.
- Public node authoring is now only the 17-name top-level `corex` function SDK.
  `ea_node_editor.nodes` is internal, its former `types.py` barrel is removed,
  and trusted descriptor decorators remain owned by the Nodes map for the exact
  internal/DPF/add-on boundary only.
- Public plugin guidance is `docs/PLUGIN_AUTHORING_GUIDE.md` plus the Signal
  Plot and strain examples under `docs/examples/`; migration failures route to
  `docs/PLUGIN_MIGRATION_GUIDE.md`. The old Signal Plot declaration is retained
  only as an internal visual fixture under `tests/fixtures/node_controls/`.
- T17 documentation corrections use
  `tests/fixtures/node_catalog/t17_non_dpf_documentation_overlay.json` through
  `tests/non_dpf_catalog_fixture.py`; the unified Media Panel structural overlay
  is applied afterward to form the 131-row current catalog, while the 133-node
  pre-cutover fixture remains frozen. Closeout evidence lives in
  `docs/specs/perf/COREX_NOVICE_PLUGIN_SDK_QA_MATRIX.md`.
- Core integrations contribute eight reserved function entries plus the trusted
  Path Pointer and Folder Explorer exceptions. SSH/SFTP contributes six reserved
  function entries, Paramiko-free value contracts, and a worker-lazy Paramiko runtime.
- Data-control, engineering import/viewer, geometry, spatial, mesh, FEM, AI,
  security, reporting, rich-value, and viewport execution declarations are in the
  reserved function bundle; their trusted contracts, services, size resolvers,
  session/handle ownership, and neutral COREX identifiers remain with the existing
  helper modules.
- Retired import and placeholder surfaces are absent from current ownership.

## Hygiene

- Update the owning map when source/test ownership moves.
- Regenerate `docs/agent_route_index.*` and
  `docs/source_test_file_index.md` after path changes.
- Run `scripts/check_agent_maps.py` after every map edit.
