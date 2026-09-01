# COREX Architecture Modernization QA Matrix

- Updated: `2026-05-01`
- Packet set: `COREX_ARCHITECTURE_MODERNIZATION`
- Packet window: `P00` through `P12`
- Integration base: `main`
- Active closeout branch: `codex/corex-architecture-modernization/p12-closeout-traceability`

## Locked Scope

This closeout covers the accepted Corex architecture modernization packet
branches, packet-local artifacts, retained verification commands, final public
architecture docs, requirement traceability, and residual risks for the
pre-release Option B baseline.

The modernization baseline keeps a GUI-independent headless Corex kernel with
the QML shell as one client, strict current `.cxproj` project loading, canonical
graph action IDs, explicit node/plugin/surface/toolchain contracts, and
execution backend policy. Packet-owned pre-release compatibility seams remain
removed instead of being restored as fallback paths.

## Final Architecture Baseline

- `ea_node_editor.execution.runtime` and the `corex-runtime` console
  entry point publish the Qt-free runtime API used by non-GUI clients and by
  the QML shell's execution boundary.
- `ea_node_editor.ui.shell.composition` binds the QML shell as a bridge-first
  client through focused library, workspace, inspector, canvas, graph-action,
  add-on, fullscreen, viewer, script, theme, status, and help surfaces.
- `.cxproj` load/save remains current-schema-only through persistence-owned
  validation and normalization; old envelopes and in-app compatibility
  migrations are not current app load paths.
- canonical graph action IDs are the only public graph verb route for
  QML/PyQt action dispatch; old graph/canvas action aliases are not restored.
- Node and plugin extension points are descriptor-first through
  `NodeTypeSpec`, `PluginDescriptor`, `RuntimeBackendSpec`, `ToolchainSpec`,
  `ArtifactDescriptor`, `SurfaceCapabilitySpec`, package manifests, and
  add-on records.
- Runtime backend selection is explicit through execution backend policy,
  process-run subprocess policy, runtime preparation caching, and optional
  trusted in-process execution only when enabled by policy.

## Packet Outcomes

| Packet | Branch Label | Accepted Commit | Outcome | Artifact |
| --- | --- | --- | --- | --- |
| P00 Bootstrap | `main` | `bootstrap-docs-current-thread` | Published packet docs, prompts, manifest, status ledger, and spec-index registration. | control-doc bootstrap only |
| P01 Requirements ADRs | `codex/corex-architecture-modernization/p01-requirements-adrs` | `a1e9e580e4ae295988145ee590fbf178da56083f` | Locked pre-release Option B requirements and ADR wording for the modernization baseline. | `P01_requirements_adrs_WRAPUP.md` |
| P02 Strict Persistence | `codex/corex-architecture-modernization/p02-strict-persistence` | `9e71ea7a5f099c155916e61eb1f80b7569925616` | Removed old-envelope project-load acceptance, fallback view-ID synthesis, and packet-owned persistence compatibility paths. | `P02_strict_persistence_WRAPUP.md` |
| P03 Canonical Actions | `codex/corex-architecture-modernization/p03-canonical-actions` | `7ecb0c3562b6e515a9901ca7989ee63b47177774` | Removed graph/canvas action aliases and enforced canonical QML command IDs. | `P03_canonical_actions_WRAPUP.md` |
| P04 Verification Registry | `codex/corex-architecture-modernization/p04-verification-registry` | `6d399c4a105e70c226ac0583523af78809dfa452` | Added the manifest-owned verification suite registry and derived runner/test consumers from it. | `P04_verification_registry_WRAPUP.md` |
| P05 Shell Composition | `codex/corex-architecture-modernization/p05-shell-composition` | `813cdc07627e89b223c15e542a2b57382ae65d86` | Split shell composition into explicit dependency bundles and focused QML host bindings. | `P05_shell_composition_WRAPUP.md` |
| P06 Canvas Facade | `codex/corex-architecture-modernization/p06-canvas-facade` | `945d24658025d6439bf12e4f6d540e175ca037a4` | Added graph-canvas facade services and removed duplicate effective-port policy paths. | `P06_canvas_facade_WRAPUP.md` |
| P07 Surface Fullscreen Input | `codex/corex-architecture-modernization/p07-surface-fullscreen-input` | `f12659f517f60e3c377d5e7f3978341f5805aa46` | Added registered surface, fullscreen, and input contracts for viewer, media, web, and stylus-ready surfaces. | `P07_surface_fullscreen_input_WRAPUP.md` |
| P08 Node Creation Wizards | `codex/corex-architecture-modernization/p08-node-creation-wizards` | `c73743e61dda619fa559fe50f1b02e87c9845041` | Added declarative wizard/profile descriptors and a Python Script creation profile. | `P08_node_creation_wizards_WRAPUP.md` |
| P09 Plugin Toolchain Contracts | `codex/corex-architecture-modernization/p09-plugin-toolchain-contracts` | `7ae7328cf41f26b6540b924c47c79867938df860` | Added canonical plugin/add-on runtime backend, toolchain, artifact, and surface capability contracts. | `P09_plugin_toolchain_contracts_WRAPUP.md` |
| P10 Headless Runtime API | `codex/corex-architecture-modernization/p10-headless-runtime-api` | `1e91e7d4f15a97348a48289878913bf82a578b10` | Added the no-GUI Corex runtime API, `corex-runtime` entry point, and shell execution boundary reuse. | `P10_headless_runtime_api_WRAPUP.md` |
| P11 Execution Backends | `codex/corex-architecture-modernization/p11-execution-backends` | `eb0d114d2e9d0179d1e9dc63ec8b2069aebe6171` | Added backend orchestration, trusted in-process opt-in, runtime preparation caching, and subprocess policy. | `P11_execution_backends_WRAPUP.md` |
| P12 Closeout Traceability | `codex/corex-architecture-modernization/p12-closeout-traceability` | `9877a327cbc66a39c61a60e7d5b4c338bc1031aa` | Publishes this final QA matrix, public-doc closeout story, traceability rows, semantic doc tests, and full verification evidence. | `P12_closeout_traceability_WRAPUP.md` |

## Retained Automated Verification

| Packet | Accepted Commit | Retained Verification |
| --- | --- | --- |
| P01 | `a1e9e580e4ae295988145ee590fbf178da56083f` | `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_dead_code_hygiene.py --ignore=venv -q`; `.\venv\Scripts\python.exe scripts/check_traceability.py`; `.\venv\Scripts\python.exe scripts/check_markdown_links.py`; review gate `tests/test_traceability_checker.py`. |
| P02 | `9e71ea7a5f099c155916e61eb1f80b7569925616` | `.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py --ignore=venv -q`; `.\venv\Scripts\python.exe -m pytest tests/test_persistence_package_imports.py tests/test_execution_artifact_refs.py --ignore=venv -q`; review gate `tests/test_serializer_schema_migration.py`. |
| P03 | `7ecb0c3562b6e515a9901ca7989ee63b47177774` | `.\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q`; `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py --ignore=venv -q`; review gate `tests/test_graph_action_contracts.py`. |
| P04 | `6d399c4a105e70c226ac0583523af78809dfa452` | `.\venv\Scripts\python.exe -m pytest tests/test_run_verification.py tests/test_pytest_defaults.py tests/test_shell_isolation_phase.py --ignore=venv -q`; `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`; review gate `tests/test_run_verification.py`. |
| P05 | `813cdc07627e89b223c15e542a2b57382ae65d86` | `$env:QT_QPA_PLATFORM = "offscreen"; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/test_shell_window_lifecycle.py tests/test_shell_project_session_controller.py tests/test_shell_run_controller.py --ignore=venv -q`; `.\venv\Scripts\python.exe -m pytest tests/test_shell_isolation_phase.py --ignore=venv -q`; review gate `tests/test_main_window_shell.py`. |
| P06 | `945d24658025d6439bf12e4f6d540e175ca037a4` | `$env:QT_QPA_PLATFORM = "offscreen"; .\venv\Scripts\python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v`; `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py --ignore=venv -q`; review gate `tests.test_graph_surface_input_contract`. |
| P07 | `f12659f517f60e3c377d5e7f3978341f5805aa46` | `$env:QT_QPA_PLATFORM = "offscreen"; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_content_fullscreen_bridge.py tests/test_embedded_viewer_overlay_manager.py tests/test_passive_image_nodes.py --ignore=venv -q`; graph-surface unittest gate; review gate `tests/test_content_fullscreen_bridge.py`. |
| P08 | `c73743e61dda619fa559fe50f1b02e87c9845041` | `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py tests/test_plugin_loader.py tests/test_package_manager.py --ignore=venv -q`; `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_workspace_library_controller_unit.py --ignore=venv -q`; review gate `tests/test_registry_validation.py`. |
| P09 | `7ae7328cf41f26b6540b924c47c79867938df860` | `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py tests/test_registry_validation.py --ignore=venv -q`; `.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py --ignore=venv -q`; `.\venv\Scripts\python.exe scripts/check_traceability.py`; review gate `tests/test_plugin_loader.py`. |
| P10 | `1e91e7d4f15a97348a48289878913bf82a578b10` | `.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_run_flow.py tests/test_run_controller_unit.py --ignore=venv -q`; `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_run_script.py --ignore=venv -q`; review gate `tests/test_execution_worker.py`. |
| P11 | `eb0d114d2e9d0179d1e9dc63ec8b2069aebe6171` | `.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_process_run_node.py tests/test_passive_runtime_wiring.py --ignore=venv -q`; `.\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_protocol.py tests/test_execution_viewer_service.py tests/test_architecture_boundaries.py --ignore=venv -q`; review gate `tests/test_process_run_node.py`. |
| P12 | `9877a327cbc66a39c61a60e7d5b4c338bc1031aa` | Final closeout commands below plus the review gate before marking the packet done. |

## Final Closeout Commands

| Command | Purpose |
| --- | --- |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_run_script.py --ignore=venv -q` | Validate P12 traceability mirrors, markdown/index hygiene, and canonical run-script docs. |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Validate semantic traceability, public-doc closeout tokens, and this QA matrix. |
| `.\venv\Scripts\python.exe scripts/check_markdown_links.py` | Validate docs/index/matrix/wrap-up local links. |
| `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --dry-run` | Enumerate the full verification workflow before running it. |
| `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full` | Execute the repo-owned full verification workflow. |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | P12 review gate before final packet closeout. |

## 2026-05-01 Execution Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_run_script.py --ignore=venv -q` | `PASS` | P12 docs, traceability, markdown hygiene, and run-script guardrail validation. |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | `PASS` | Semantic traceability gate. |
| `.\venv\Scripts\python.exe scripts/check_markdown_links.py` | `PASS` | Markdown local-link gate. |
| `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --dry-run` | `PASS` | Full verification dry-run enumeration. |
| `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full` | `FAIL` | Fast phase stopped with `5 failed, 1053 passed, 1 skipped, 56 warnings in 47.29s`; two execution-client failures passed in the focused serial rerun, while `tests/test_main_bootstrap.py::AppBootstrapTests::test_build_shell_window_composition_returns_typed_contract`, `tests/test_group_backdrop_contracts.py::GroupBackdropSurfaceQmlTests::test_graph_node_host_loads_group_backdrop_surface_family`, and `tests/test_group_backdrop_interactions.py::GroupBackdropInteractionTests::test_graph_canvas_scene_state_skips_edge_redraw_for_group_backdrop_live_resize` still failed serially. Owner: Corex UI/runtime regression owner before release. Reproduction: `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full`; focused reproduction: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest -n 0 tests/test_main_bootstrap.py::AppBootstrapTests::test_build_shell_window_composition_returns_typed_contract tests/test_group_backdrop_contracts.py::GroupBackdropSurfaceQmlTests::test_graph_node_host_loads_group_backdrop_surface_family tests/test_group_backdrop_interactions.py::GroupBackdropInteractionTests::test_graph_canvas_scene_state_skips_edge_redraw_for_group_backdrop_live_resize --ignore=venv -q`. |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | `PASS` | P12 review gate. |

## Produced Artifacts

- `docs/specs/perf/COREX_ARCHITECTURE_MODERNIZATION_QA_MATRIX.md`
- `docs/specs/work_packets/corex_architecture_modernization/P12_closeout_traceability_WRAPUP.md`
- `docs/specs/work_packets/corex_architecture_modernization/COREX_ARCHITECTURE_MODERNIZATION_STATUS.md`

## Manual Smoke Guidance

Ready for manual testing after the final closeout commands pass.

1. Launch the QML shell with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`; expected result: the shell opens as a client of the headless Corex/runtime boundaries.
2. Save and reopen a current `.cxproj` project; expected result: current-schema validation and normalization succeed, while pre-current documents remain offline-conversion inputs.
3. Run a small workflow through the shell and through `corex-runtime`; expected result: both routes use the same headless runtime API, backend selection policy, runtime snapshot, and worker protocol.
4. Open an add-on or DPF-backed node when its dependency is unavailable and then available; expected result: unavailable add-on projections stay locked and descriptor-driven, and live backend availability returns through the add-on/runtime rebuild path.

## Residual Risks

- Existing Ansys DPF operator rename deprecation warnings remain unrelated to P12 closeout.
- Full verification is not green on this branch. Owner: Corex UI/runtime regression owner before release. Reproduction: `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full`; focused serial reproduction for the remaining product regressions is `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest -n 0 tests/test_main_bootstrap.py::AppBootstrapTests::test_build_shell_window_composition_returns_typed_contract tests/test_group_backdrop_contracts.py::GroupBackdropSurfaceQmlTests::test_graph_node_host_loads_group_backdrop_surface_family tests/test_group_backdrop_interactions.py::GroupBackdropInteractionTests::test_graph_canvas_scene_state_skips_edge_redraw_for_group_backdrop_live_resize --ignore=venv -q`.
- External workflow adapters and native Rust/C++ build execution remain future work; P09/P11 only publish contracts, artifact descriptors, backend policy, and cache seams.
- Process resource hints are captured by policy but are not enforced as OS CPU or memory limits.
- Desktop-only live DPF/PyVista/Qt validation still depends on local optional backend availability; automated tests cover the contract and projection behavior with fixtures.
