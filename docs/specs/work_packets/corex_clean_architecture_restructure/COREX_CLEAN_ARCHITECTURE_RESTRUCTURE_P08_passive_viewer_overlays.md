# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P08: Passive Viewer Overlays

## Objective

Split passive media, viewer session, fullscreen, overlay geometry, preview capture, and binder/session orchestration into clear presentation service and adapter boundaries.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, active user edits in overlay files, and viewer/passive tests needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P07_qml_graph_canvas_core` is `PASS`.
- The worker has inspected current uncommitted/user-owned edits in embedded viewer overlay and comment popover surfaces before changing overlapping files.

## Execution Dependencies

- `P07_qml_graph_canvas_core`

## Target Subsystems

- Passive graph media surfaces
- Viewer QML surfaces
- Viewer session bridge and backend viewer service adapters
- Content fullscreen bridge
- Embedded viewer overlay manager
- Viewer/overlay/fullscreen tests

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/graph/passive/**`
- `ea_node_editor/ui_qml/components/graph/viewer/**`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `ea_node_editor/execution/viewer_*.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_host_service.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_content_fullscreen_bridge.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P08_passive_viewer_overlays_WRAPUP.md`

## Required Behavior

- Keep backend `ViewerSessionService` explicit and separate from QML presentation adapters.
- Move artifact resolution, temp preview management, fullscreen policy, overlay geometry, and binder orchestration behind clearer application/presentation services.
- Keep `viewer_session_bridge.py`, `viewer_host_service.py`, `content_fullscreen_bridge.py`, and overlay manager as thin adapters where feasible.
- Preserve viewer reopen/rerun behavior, fullscreen behavior, passive media preview/edit/repair flows, and embedded overlay positioning.

## Non-Goals

- Do not change runtime protocol DTOs owned by `P01` except through compatibility adapters.
- Do not restructure graph-canvas routing owned by `P07`.
- Do not overwrite user-owned comment popover or overlay changes without incorporating them.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_execution_viewer_service.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P08_passive_viewer_overlays_WRAPUP.md`

## Acceptance Criteria

- Viewer presentation responsibilities are separated from backend session state and artifact sidecar ownership.
- Existing passive media, viewer, fullscreen, and overlay behavior remains compatible.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

This packet is intentionally isolated in its own recommended fresh executor thread because the viewer/overlay context is large and overlaps active user work.
