# CTRL_CANVAS_INSERT_MENU P04: Regression Docs Traceability

## Objective
- Refresh requirements, QA/traceability docs, and packet-scoped final regression evidence for the Ctrl-canvas insert menu, text annotation workflow, and stylus placeholder.

## Preconditions
- `P00` is marked `PASS` in [CTRL_CANVAS_INSERT_MENU_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_STATUS.md).
- No later `CTRL_CANVAS_INSERT_MENU` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`

## Target Subsystems
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md`
- `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md`

## Conservative Write Scope
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md`
- `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/P04_regression_docs_traceability_WRAPUP.md`

## Required Behavior
- Update requirements and traceability docs so the shipped behavior is explicitly covered:
  - `Ctrl+Double Left Click` empty-canvas insert menu
  - `passive.annotation.text` node contract
  - typography style fields for passive text annotations
  - inline body editing reuse of pending-surface-action and `nodeOpenRequested`
  - stylus placeholder as a hint-only, non-persistent non-goal
- Extend the relevant QA/manual docs so they cover the new gesture, text-node creation path, inline/inspector body editing, typography rendering expectations, and the stylus coming-soon hint.
- Carry forward the passive annotation, media, comment-backdrop, and passive-style regression expectations from the earlier packets so the final docs and aggregate regression evidence still reflect the original feature-test plan.
- Keep the docs aligned with the actual implemented scope from `P01` through `P03`. If the current requirements pack lacks a precise anchor, extend the closest existing passive/input requirements or add a new requirement id in-scope rather than leaving the feature undocumented.
- Run the packet-scoped final regression and traceability commands. Do not widen into repo-wide full verification flows when the packet-owned commands already prove the feature.

## Non-Goals
- No new runtime behavior beyond documentation and regression close-out.
- No fixture regeneration unless a packet-owned doc cannot be updated accurately without it.
- No stylus implementation beyond documenting the placeholder scope.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_planning_annotation_catalog tests.test_passive_style_dialogs tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.main_window_shell.shell_runtime_contracts tests.main_window_shell.drop_connect_and_workflow_io tests.main_window_shell.passive_property_editors tests.main_window_shell.passive_style_context_menus -v`
2. `./venv/Scripts/python.exe scripts/check_traceability.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/ctrl_canvas_insert_menu/P04_regression_docs_traceability_WRAPUP.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md`
- `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md`

## Acceptance Criteria
- Requirement and traceability docs accurately describe the final Ctrl-canvas insert menu, text annotation contract, inline editing behavior, typography fields, and stylus placeholder scope.
- QA/manual docs cover the new gesture, text insertion, body editing sync, typography rendering expectations, stylus hint path, and the carried-forward passive annotation/media/comment-backdrop and passive-style regression expectations.
- The packet-scoped final regression command passes, and `scripts/check_traceability.py` passes.

## Handoff Notes
- This is the final packet in the set. The wrap-up must summarize the final verification commands and any remaining manual checks the executor should mention before merge.
- If the packet extends existing requirement ids instead of creating new ids, call that out explicitly in the wrap-up so later reviewers can reconcile the traceability delta quickly.
