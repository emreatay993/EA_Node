# P10 Boundary Regression Docs Wrap-Up

## Implementation Summary

- Documented the post-refactor shell/scene/QML ownership split in `ARCHITECTURE.md`, including the focused shell facade bridges, `GraphCanvas` host adapter, and the internal `GraphSceneBridge` helper seams.
- Updated `TODO.md` to record the completed boundary refactor and to track the still-open serializer image-panel regression and Windows Qt/QML multi-`ShellWindow` lifetime issue separately from this packet set.
- Extended `docs/specs/requirements/TRACEABILITY_MATRIX.md` so the boundary ownership seams, `GraphCanvas` contract, and closeout QA artifacts are traceable to the existing architecture/UI/QA requirements.
- Added `docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_QA_MATRIX.md` with the approved targeted regression commands, the passing P10 aggregate command, and the environment-specific execution notes discovered during closeout.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graphics_settings_preferences tests.test_graph_theme_preferences tests.test_shell_project_session_controller tests.test_main_window_shell tests.test_shell_run_controller tests.test_workspace_library_controller_unit tests.test_graph_track_b tests.test_inspector_reflection tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_property_editors tests.test_passive_image_nodes tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_graph_theme_shell tests.test_pdf_preview_provider -v` (`288` tests, `217.110s`)
- PASS: `git diff --check -- ARCHITECTURE.md TODO.md docs/specs/requirements/TRACEABILITY_MATRIX.md docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_QA_MATRIX.md docs/specs/work_packets/shell_scene_boundary/P10_boundary_regression_docs_WRAPUP.md`

## Manual Test Directives

Ready for manual testing

1. Prerequisite: launch the app from a fresh desktop process with the project venv so Qt has a normal display session.
   Action: open the main shell and verify the node library, graph canvas, inspector, workspace tabs, and console all render together.
   Expected: the shell loads without missing-context warnings and the standard shell panes respond normally.
2. Action: drag from a node port to empty canvas space to open quick insert, accept a compatible result, then use graph search and inspector selection on the inserted node.
   Expected: quick insert/search route through the shell bridge surfaces, the inserted node auto-connects, and inspector metadata follows the selected node.
3. Action: multi-select two nodes and drag them together, then edit an image or PDF panel path inline or through browse, save the project, and reopen it.
   Expected: grouped drag stays in sync, media previews resolve, and the restored project keeps the authored media/inspector state.

## Residual Risks

- The known passive image-panel serializer regression that adds default crop fields during round-trip remains a separate persistence backlog item and was not reopened by P10.
- Windows Qt/QML lifetime instability for repeated `ShellWindow()` construction in one interpreter is still a broader test-environment constraint; keep shell-backed verification on fresh-process commands and existing subprocess-isolation loaders.
- Raw compatibility context properties remain exposed while the focused shell bridges are the preferred ownership seam. That compatibility surface is intentional, but future cleanup should remove it only after all consumers are migrated.

## Ready for Integration

Yes. The required combined boundary regression slice passed, the closeout documentation is updated inside the allowed write scope, and the remaining issues are explicitly recorded as separate baseline follow-ups rather than blockers for this refactor.
