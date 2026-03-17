# SHELL_SCENE_BOUNDARY P10: Boundary Regression Docs

## Objective
- Run the combined shell/scene/boundary regression slice and close the architecture, traceability, and QA documentation for the `SHELL_SCENE_BOUNDARY` refactor.

## Preconditions
- `P01` through `P09` are marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`
- `P04`
- `P05`
- `P06`
- `P07`
- `P08`
- `P09`

## Target Subsystems
- `ARCHITECTURE.md`
- `TODO.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_QA_MATRIX.md` (new)
- `docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md`

## Conservative Write Scope
- `ARCHITECTURE.md`
- `TODO.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_QA_MATRIX.md`
- `docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md`

## Required Behavior
- Run the combined boundary regression slice covering:
  - settings/theme preference normalization
  - shell/QML host loading and controller flows
  - GraphCanvas boundary behavior
  - `GraphSceneBridge` state/mutation/payload behavior
  - passive graph-surface integration paths touched by the refactor
- Add `SHELL_SCENE_BOUNDARY_QA_MATRIX.md` summarizing the approved regression commands and any environment-specific execution notes discovered while closing the refactor.
- Update `ARCHITECTURE.md`, `TODO.md`, and `TRACEABILITY_MATRIX.md` so the new shell/QML boundary ownership is documented and traceable.
- Record any still-open baseline issues separately from this refactor, including the known serializer image-panel failure if it is rechecked during closeout.

## Non-Goals
- No new feature work.
- No widening into persistence/schema repair unless a prior packet introduced a fresh regression.
- No reopening earlier packets except for minimal follow-up edits required to make the documented regression slice pass.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graphics_settings_preferences tests.test_graph_theme_preferences tests.test_shell_project_session_controller tests.test_main_window_shell tests.test_shell_run_controller tests.test_workspace_library_controller_unit tests.test_graph_track_b tests.test_inspector_reflection tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_property_editors tests.test_passive_image_nodes tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_graph_theme_shell tests.test_pdf_preview_provider -v`

## Acceptance Criteria
- The combined boundary regression slice passes.
- Architecture/traceability/QA docs clearly describe the new shell/scene/QML boundary ownership.
- Any still-open baseline issues are recorded explicitly instead of being silently folded into the refactor scope.

## Handoff Notes
- This packet completes the `SHELL_SCENE_BOUNDARY` packet set.
- If the serializer image-panel regression is still failing when rechecked manually, record it as a separate follow-up rather than retroactively widening this packet set.
