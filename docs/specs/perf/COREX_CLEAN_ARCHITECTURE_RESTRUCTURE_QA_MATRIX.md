# COREX Clean Architecture Restructure QA Matrix

- Updated: `2026-04-25`
- Packet set: `COREX_CLEAN_ARCHITECTURE_RESTRUCTURE`
- Packet window: `P00` through `P12`
- Integration base: `main`
- Wave base revision: `725add98dedfbad3785022de1bf07187c451f309`
- Target merge branch: `main`
- Active closeout branch: `codex/corex-clean-architecture-restructure/p12-docs-traceability-closeout`

## Locked Scope

This closeout covers the accepted clean-architecture restructure packet branches,
their substantive commits, retained packet verification, public launch
documentation, closeout artifacts, and residual risks for the behavior-preserving
ownership split layered on top of the completed no-legacy baseline.

The shared status ledger is executor-owned. This matrix records P12 closeout
evidence without changing `COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_STATUS.md`.

## Final Ownership Boundaries

- `ea_node_editor.execution` owns runtime contracts, snapshot assembly,
  protocol/client/worker flow, and execution-time payloads.
- `ea_node_editor.graph` owns graph domain objects, hierarchy, effective-port
  rules, transforms, and graph-state mutation boundaries.
- `ea_node_editor.workspace` and `ea_node_editor.custom_workflows` own workspace
  ordering, active selection, custom-workflow identity, import/export, and
  user-global/project-local workflow stores.
- `ea_node_editor.persistence` owns current-schema `.sfe` validation,
  serializers/codecs, unresolved add-on envelopes, artifact/session/autosave
  stores, and legacy-document rejection.
- `ea_node_editor.ui.shell.composition` owns shell construction and focused
  shell/QML context wiring; `ShellWindow` remains the host/facade.
- `ea_node_editor.ui_qml` owns shell roots, graph-canvas ports, graph-scene
  bridge helper seams, viewer/fullscreen/content surfaces, and QML presentation.
- `ea_node_editor.nodes` owns the node SDK, descriptor registry, package IO, and
  descriptor-first plugin discovery; `ea_node_editor.addons` owns add-on catalog,
  enablement, backend selection, and hot-apply lifecycle.
- Cross-cutting shell theme, graph theme, status, and telemetry formatting live
  behind explicit service/bridge surfaces rather than raw QML globals.

## Packet Outcomes

| Packet | Branch Label | Accepted Substantive Commit | Outcome | Artifact |
| --- | --- | --- | --- | --- |
| P00 Bootstrap | `main` | `bootstrap-docs-current-thread` | Published packet docs, prompts, manifest, and status ledger. | control-doc bootstrap only |
| P01 Runtime Contracts | `codex/corex-clean-architecture-restructure/p01-runtime-contracts` | `2283635deb1d65f1973720c3f500a5c1620d6ac9` | Moved runtime value serialization into passive `runtime_contracts` and preserved execution compatibility exports. | [P01 wrap-up](../work_packets/corex_clean_architecture_restructure/P01_runtime_contracts_WRAPUP.md) |
| P02 Graph Domain Mutation | `codex/corex-clean-architecture-restructure/p02-graph-domain-mutation` | `c561344a03c13d911293bed47b65f94f6a9b1d45` | Centralized graph dirty marking, active-view fallback, default-view repair, and view mutations behind graph-owned domain APIs. | [P02 wrap-up](../work_packets/corex_clean_architecture_restructure/P02_graph_domain_mutation_WRAPUP.md) |
| P03 Workspace Custom Workflows | `codex/corex-clean-architecture-restructure/p03-workspace-custom-workflows` | `f7c70c4d05abed6c4000230556c963f55e6bfd2e` | Kept workspace order and active selection in `WorkspaceManager` while enforcing explicit custom-workflow IDs. | [P03 wrap-up](../work_packets/corex_clean_architecture_restructure/P03_workspace_custom_workflows_WRAPUP.md) |
| P04 Current Schema Persistence | `codex/corex-clean-architecture-restructure/p04-current-schema-persistence` | `3547e17ecd5bdab4e8be61779110d8528ca3c61c` | Moved runtime persistence-envelope ownership into persistence and kept artifact/session state outside project semantics. | [P04 wrap-up](../work_packets/corex_clean_architecture_restructure/P04_current_schema_persistence_WRAPUP.md) |
| P05 Shell Composition | `codex/corex-clean-architecture-restructure/p05-shell-composition` | `29d8e3851eed6df9288affd2ba13dffc3d167768` | Moved shell dependency creation into `composition.py` and split add-on/run/presenter host behavior. | [P05 wrap-up](../work_packets/corex_clean_architecture_restructure/P05_shell_composition_WRAPUP.md) |
| P06 QML Shell Roots | `codex/corex-clean-architecture-restructure/p06-qml-shell-roots` | `bfd41d501932335d77bb42edc09157aae4f1f7c9` | Routed shell-level QML services through explicit root-owned properties and focused bridge contracts. | [P06 wrap-up](../work_packets/corex_clean_architecture_restructure/P06_qml_shell_roots_WRAPUP.md) |
| P07 QML Graph Canvas Core | `codex/corex-clean-architecture-restructure/p07-qml-graph-canvas-core` | `9887d87bb2b6762db71fe6e7ec2215f2db5af848` | Added graph-canvas feature-root action routing and completed comment-backdrop title-icon contract remediation. | [P07 wrap-up](../work_packets/corex_clean_architecture_restructure/P07_qml_graph_canvas_core_WRAPUP.md) |
| P08 Passive Viewer Overlays | `codex/corex-clean-architecture-restructure/p08-passive-viewer-overlays` | `9a685b021adc0011cfa348c3587d2d095e64578a` | Split viewer session, viewer host, fullscreen, and embedded overlay presentation services behind thin adapters. | [P08 wrap-up](../work_packets/corex_clean_architecture_restructure/P08_passive_viewer_overlays_WRAPUP.md) |
| P09 Nodes SDK Registry | `codex/corex-clean-architecture-restructure/p09-nodes-sdk-registry` | `09f50d4099d39e6c3b3172027a21acbda923a680` | Made node SDK/runtime/viewer contracts explicit and removed direct persistence-envelope dependency from runtime snapshots. | [P09 wrap-up](../work_packets/corex_clean_architecture_restructure/P09_nodes_sdk_registry_WRAPUP.md) |
| P10 Plugin Add-On Descriptor | `codex/corex-clean-architecture-restructure/p10-plugin-addon-descriptor` | `d6fb309606bb209b7dbccb35ecf746c33ffa0626` | Moved add-on discovery, enablement filtering, backend selection, and cache invalidation into add-on-owned surfaces. | [P10 wrap-up](../work_packets/corex_clean_architecture_restructure/P10_plugin_addon_descriptor_WRAPUP.md) |
| P11 Cross-Cutting Services | `codex/corex-clean-architecture-restructure/p11-cross-cutting-services` | `b1fc5fb3b359be5bf940ff0d23dddab10b4194f0` | Added shell-theme, graph-theme, and shell-status services behind existing QML/presenter adapters. | [P11 wrap-up](../work_packets/corex_clean_architecture_restructure/P11_cross_cutting_services_WRAPUP.md) |
| P12 Docs Traceability Closeout | `codex/corex-clean-architecture-restructure/p12-docs-traceability-closeout` | `be9e89ad8e78597a11a8e582fcb925298b13cf79` | Publishes final architecture docs, QA matrix, public launch-doc cleanup, and closeout test updates. | [P12 wrap-up](../work_packets/corex_clean_architecture_restructure/P12_docs_traceability_closeout_WRAPUP.md) |

## Retained Automated Verification

| Packet | Accepted Commit | Retained Verification |
| --- | --- | --- |
| P01 | `2283635deb1d65f1973720c3f500a5c1620d6ac9` | `.\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_protocol.py tests/test_architecture_boundaries.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py --ignore=venv`; review gate `tests/test_architecture_boundaries.py`; validator PASS. |
| P02 | `c561344a03c13d911293bed47b65f94f6a9b1d45` | `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_surface_input_contract.py tests/test_graph_track_b.py --ignore=venv`; PowerShell-expanded `tests/test_graph*.py` set; review gate `tests/test_architecture_boundaries.py`; validator PASS. |
| P03 | `f7c70c4d05abed6c4000230556c963f55e6bfd2e` | `.\venv\Scripts\python.exe -m pytest tests/test_workspace_library_controller_unit.py tests/test_workspace_manager.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py --ignore=venv`; review gate `tests/test_workspace_library_controller_unit.py`; validator PASS. |
| P04 | `3547e17ecd5bdab4e8be61779110d8528ca3c61c` | `.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/test_execution_artifact_refs.py tests/test_persistence_package_imports.py --ignore=venv`; review gate `tests/test_serializer_schema_migration.py`; validator PASS. |
| P05 | `29d8e3851eed6df9288affd2ba13dffc3d167768` | `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/test_shell_window_lifecycle.py tests/test_shell_project_session_controller.py tests/test_shell_run_controller.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/test_shell_isolation_phase.py --ignore=venv`; review gate `tests/test_main_window_shell.py`; validator PASS. |
| P06 | `bfd41d501932335d77bb42edc09157aae4f1f7c9` | `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_action_contracts.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/main_window_shell --ignore=venv`; review gate `tests/test_graph_action_contracts.py`; validator PASS. |
| P07 | `9887d87bb2b6762db71fe6e7ec2215f2db5af848` | `.\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/test_comment_backdrop_contracts.py tests/test_passive_runtime_wiring.py --ignore=venv`; review gate `tests/test_graph_surface_input_contract.py`; validator PASS. |
| P08 | `9a685b021adc0011cfa348c3587d2d095e64578a` | `.\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_execution_viewer_service.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv`; review gate `tests/test_embedded_viewer_overlay_manager.py`; validator PASS. |
| P09 | `09f50d4099d39e6c3b3172027a21acbda923a680` | `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_registry_validation.py tests/test_package_manager.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/test_dpf_library_taxonomy.py tests/test_dpf_node_catalog.py tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py --ignore=venv`; `tests/test_architecture_boundaries.py`; review gate `tests/test_registry_validation.py`; validator PASS. |
| P10 | `d6fb309606bb209b7dbccb35ecf746c33ffa0626` | `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py --ignore=venv`; review gate `tests/test_plugin_loader.py`; validator PASS. |
| P11 | `b1fc5fb3b359be5bf940ff0d23dddab10b4194f0` | `.\venv\Scripts\python.exe -m pytest tests/test_shell_theme.py tests/test_graph_theme_preferences.py --ignore=venv`; `.\venv\Scripts\python.exe -m pytest tests/test_project_session_controller_unit.py tests/test_main_window_shell.py --ignore=venv`; review gate `tests/test_graph_theme_preferences.py`; validator PASS. |

## Final Closeout Commands

| Command | Purpose |
| --- | --- |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_run_script.py --ignore=venv` | Validate P12 traceability mirrors, markdown/index hygiene, and canonical shell script launch expectations. |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Validate the semantic traceability baseline retained from the no-legacy closeout and current public architecture docs. |
| `.\venv\Scripts\python.exe scripts/check_markdown_links.py` | Validate local links across docs, the spec index, packet docs, and this QA matrix. |

## 2026-04-25 Execution Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_run_script.py --ignore=venv` | `PASS` | 90 tests passed; pytest printed a non-fatal Windows temp cleanup `PermissionError` after successful exit. |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | `PASS` | Reported `TRACEABILITY CHECK PASS`. |
| `.\venv\Scripts\python.exe scripts/check_markdown_links.py` | `PASS` | Reported `MARKDOWN LINK CHECK PASS`. |

## Produced Artifacts

- `docs/specs/perf/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_QA_MATRIX.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P12_docs_traceability_closeout_WRAPUP.md`

## Manual Smoke Guidance

Ready for manual testing after the final closeout commands pass.

1. Launch from source with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`, or from an editable install with `.\venv\Scripts\corex-node-editor.exe`; expected result: the shell opens without relying on a root `main.py` path.
2. Open a small graph, add or edit nodes, save, and reopen; expected result: graph edits use graph-owned mutation paths and current-schema persistence round-trips without introducing legacy overlays.
3. Open Graphics Settings and switch shell/graph theme options; expected result: shell theme, graph theme, and status surfaces update through the explicit service/bridge path retained by P11.

## Residual Risks

- Existing Ansys DPF deprecation warnings from earlier packet verification remain non-blocking and outside P12 scope.
- Desktop DPF live-viewer validation still depends on local Ansys DPF, PyVista, VTK, and Qt availability; retained automated tests cover the transport and host contracts with fixtures.
- Shell-backed Qt/QML suites still require fresh-process execution on Windows because repeated `ShellWindow()` construction in one interpreter remains unreliable.
- Generated architecture diagram artifacts can lag source Mermaid blocks until `.\venv\Scripts\python.exe .\scripts\export_architecture_diagrams.py` is run; P12 did not edit Mermaid blocks or generated diagram assets.
