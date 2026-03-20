# QA and Acceptance Requirements

## Test Layers
- `REQ-QA-001`: Unit tests for registry filters, serializer round trip, workspace manager behavior.
- `REQ-QA-002`: Engine tests for run completed and run failed event paths.
- `REQ-QA-003`: Integration smoke test for Excel -> transform -> Excel pipeline.

## Functional Scenarios
- `REQ-QA-004`: Workspace lifecycle scenario test.
- `REQ-QA-005`: Multi-view state retention scenario test.
- `REQ-QA-006`: Node collapse and exposed-port behavior test.
- `REQ-QA-007`: Failure focus and error reporting test.
- `REQ-QA-008`: A combined regression gate shall cover subnode/custom-workflow persistence, graph interactions, shell/controller flows, and execution compile/runtime behavior.
- `REQ-QA-009`: a graphics-settings regression gate shall cover app-preferences persistence, settings dialogs, shell menu wiring, theme application, and canvas preference behavior.
- `REQ-QA-010`: a graph-theme regression gate shall cover graph-theme preference normalization, runtime bridge resolution, graphics-settings dialog graph-theme controls, graph-theme editor dialog/library flows, shell-theme interaction, graph scene payload theming, main-window shell integration, and project/session isolation.
- `REQ-QA-011`: a passive-node final regression gate shall cover registry contracts, serializer/migration, runtime exclusion, graph scene/host routing, passive property editors, style dialogs/presets, and local media preview support.
- `REQ-QA-012`: the repo shall carry a reference passive workspace plus a short manual visual checklist for reopen, media-preview, and preset-round-trip verification.
- `REQ-QA-013`: a graph-surface input regression gate shall cover host body routing, embedded interactive-rect ownership, modal whole-surface locks, shared inline editors, media-surface controls, and graph-surface shell workflows; if an aggregate shell wrapper is unstable, the approved fresh-process fallback shall be recorded alongside a complete targeted matrix.

## Verification Workflow
- `REQ-QA-014`: the repo shall document `scripts/run_verification.py` as the developer-oriented verification entry point with stable `fast`, `gui`, `slow`, and `full` modes.
- `REQ-QA-015`: the documented `full` workflow shall run `tests/test_shell_isolation_phase.py` as a dedicated fresh-process shell-isolation phase after the non-shell pytest phases, with target catalogs covering `tests.test_main_window_shell`, `tests.test_script_editor_dock`, `tests.test_shell_run_controller`, and `tests.test_shell_project_session_controller`.
- `REQ-QA-016`: the documented verification workflow shall record that xdist-enabled phases resolve an explicit max-worker count as `psutil.cpu_count(logical=True)` when available, else `os.cpu_count()`, else `1`, and fall back to serial pytest when `pytest-xdist` is unavailable.
- `REQ-QA-017`: the documented verification workflow shall keep unresolved out-of-scope baseline failures explicit in the QA matrix instead of claiming a fully green aggregate when known baselines remain open.
- `REQ-QA-018`: the repo shall publish a graph-canvas performance QA matrix that records the approved real-`GraphCanvas.qml` benchmark commands, sample sizes, environment limits, and any still-required interactive desktop/manual follow-up.

## Acceptance
- `AC-REQ-QA-001-01`: Included unit tests pass in CI/local runner, and the documented local default loop is `./venv/Scripts/python.exe scripts/run_verification.py --mode fast`.
- `AC-REQ-QA-004-01`: Workspace actions preserve correct tab-state and model state.
- `AC-REQ-QA-007-01`: Failed run centers node and reports exception details.
- `AC-REQ-QA-008-01`: `./venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_graph_track_b tests.test_main_window_shell tests.test_workspace_library_controller_unit tests.test_execution_worker -v` passes without regressions.
- `AC-REQ-QA-009-01`: `./venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_graphics_settings_preferences tests.test_graphics_settings_dialog tests.test_workflow_settings_dialog tests.test_shell_theme tests.test_graph_track_b tests.test_main_window_shell tests.test_shell_project_session_controller -v` passes without regressions.
- `AC-REQ-QA-010-01`: `./venv/Scripts/python.exe -m unittest tests.test_graph_theme_preferences tests.test_graph_theme_shell tests.test_graph_theme_editor_dialog tests.test_graphics_settings_preferences tests.test_graphics_settings_dialog tests.test_shell_theme tests.test_graph_track_b tests.test_main_window_shell tests.test_shell_project_session_controller -v` passes without regressions.
- `AC-REQ-QA-011-01`: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_registry_validation tests.test_registry_filters tests.test_serializer tests.test_serializer_schema_migration tests.test_execution_worker tests.test_graph_track_b tests.test_main_window_shell tests.test_inspector_reflection tests.test_passive_node_contracts tests.test_passive_runtime_wiring tests.test_passive_visual_metadata tests.test_passive_property_editors tests.test_passive_graph_surface_host tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_passive_flowchart_catalog tests.test_flowchart_visual_polish tests.test_planning_annotation_catalog tests.test_passive_style_dialogs tests.test_passive_style_presets tests.test_passive_image_nodes tests.test_pdf_preview_provider -v` passes without regressions.
- `AC-REQ-QA-012-01`: `tests/fixtures/passive_nodes/reference_flowchart.sfe` plus `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md` provide a repeatable manual check for passive-only save/load, labeled `flow` edges, media previews, and style-preset reopen behavior.
- `AC-REQ-QA-013-01`: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v`, `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes -v`, and `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_pdf_nodes -v` pass without regressions, or the approved fresh-process fallback recorded in `docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md` covers the same matrix completely.
- `AC-REQ-QA-014-01`: `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run` enumerates the approved `fast`, `gui`, `slow`, and `full` workflow recorded in `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md`.
- `AC-REQ-QA-015-01`: the documented `full` workflow keeps `tests/test_shell_isolation_phase.py` as a dedicated fresh-process shell-isolation phase after the non-shell pytest phases, and that phase covers the target catalogs for `tests.test_main_window_shell`, `tests.test_script_editor_dock`, `tests.test_shell_run_controller`, and `tests.test_shell_project_session_controller`.
- `AC-REQ-QA-016-01`: `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` records the explicit max-worker resolution algorithm and current `pytest-xdist` fallback expectation for the project venv.
- `AC-REQ-QA-017-01`: `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` records the current serializer baseline status, including the retired `passive_image_panel_properties_and_size` spot-check when no out-of-scope baseline remains and any new baseline before the aggregate is claimed fully green.
- `AC-REQ-QA-018-01`: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_docs`, `./venv/Scripts/python.exe scripts/check_traceability.py`, `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`, and `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` stay aligned.

## Current Closeout Evidence
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_QA_MATRIX.md` summarizes the accepted `ARCH_SIXTH_PASS` packet outcomes, the current proof commands, and the carried-forward residual risks for this architecture/docs closeout baseline.
