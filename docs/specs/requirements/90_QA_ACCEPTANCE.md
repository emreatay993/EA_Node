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

## Acceptance
- `AC-REQ-QA-001-01`: Included unit tests pass in CI/local runner.
- `AC-REQ-QA-004-01`: Workspace actions preserve correct tab-state and model state.
- `AC-REQ-QA-007-01`: Failed run centers node and reports exception details.
- `AC-REQ-QA-008-01`: `venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_graph_track_b tests.test_main_window_shell tests.test_workspace_library_controller_unit tests.test_execution_worker -v` passes without regressions.
- `AC-REQ-QA-009-01`: `venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_graphics_settings_preferences tests.test_graphics_settings_dialog tests.test_workflow_settings_dialog tests.test_shell_theme tests.test_graph_track_b tests.test_main_window_shell tests.test_shell_project_session_controller -v` passes without regressions.
- `AC-REQ-QA-010-01`: `venv/Scripts/python.exe -m unittest tests.test_graph_theme_preferences tests.test_graph_theme_shell tests.test_graph_theme_editor_dialog tests.test_graphics_settings_preferences tests.test_graphics_settings_dialog tests.test_shell_theme tests.test_graph_track_b tests.test_main_window_shell tests.test_shell_project_session_controller -v` passes without regressions.
- `AC-REQ-QA-011-01`: `QT_QPA_PLATFORM=offscreen venv/Scripts/python.exe -m unittest tests.test_registry_validation tests.test_registry_filters tests.test_serializer tests.test_serializer_schema_migration tests.test_execution_worker tests.test_graph_track_b tests.test_main_window_shell tests.test_inspector_reflection tests.test_passive_node_contracts tests.test_passive_runtime_wiring tests.test_passive_visual_metadata tests.test_passive_property_editors tests.test_passive_graph_surface_host tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_passive_flowchart_catalog tests.test_flowchart_visual_polish tests.test_planning_annotation_catalog tests.test_passive_style_dialogs tests.test_passive_style_presets tests.test_passive_image_nodes tests.test_pdf_preview_provider -v` passes without regressions.
- `AC-REQ-QA-012-01`: `tests/fixtures/passive_nodes/reference_flowchart.sfe` plus `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md` provide a repeatable manual check for passive-only save/load, labeled `flow` edges, media previews, and style-preset reopen behavior.
