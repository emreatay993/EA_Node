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
- [Surface Input And Inline Controls](feature_routes/surface_input_and_inline_controls.md)
- [Port Availability And Default Values](feature_routes/port_availability_and_default_values.md)
- [Plotter Nodes](feature_routes/plotter_nodes.md)
- [Neutral CAD/FE Engineering Viewer](feature_routes/neutral_cad_fe_engineering_viewer.md)
- [Ansys DPF Operator Viewer Transport](feature_routes/ansys_dpf_operator_viewer_transport.md)
- [Managed Artifacts And Project Data](feature_routes/managed_artifacts_project_data.md)
- [Project Session Files And Managed Artifacts](feature_routes/project_session_files_managed_artifacts.md)
- [Workspace Tabs, Library, And Context Menus](feature_routes/workspace_tabs_library_context_menus.md)
- [SSH/SFTP Nodes](feature_routes/ssh_sftp_nodes.md)
- [Performance Harness And Graph Stress](feature_routes/performance_harness_graph_stress.md)

## Current ownership notes

- Signal Plot behavior is owned by `nodes/builtins/plot/signal.py`,
  `execution/signal_plot_renderer.py`, and the plotter route.
- Declarative node controls are shared metadata-to-QML behavior owned by the
  node registry, graph-scene projection, and shared graph controls. Rendered
  list/group/control geometry belongs to Surface Input; payload and settings-band
  calculation belongs to Graph Scene Payload.
- Exact feature-map citations own QML components when present; the broader QML
  or graph-canvas subsystem remains the fallback only when no feature map cites
  that exact component path.
- Decorator-driven Python Script declarations are owned jointly by the node
  registry/parser, graph-owned atomic Apply, worker revalidation, and generic persistence.
- Geometry, spatial, mesh, FEM, voxel, security, reporting, media, and unit
  contracts use neutral COREX identifiers and functional module names.
- Retired import and placeholder surfaces are absent from current ownership.

## Hygiene

- Update the owning map when source/test ownership moves.
- Regenerate `docs/agent_route_index.*` and
  `docs/source_test_file_index.md` after path changes.
- Run `scripts/check_agent_maps.py` after every map edit.
