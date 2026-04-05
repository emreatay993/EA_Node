# UI_CONTEXT_SCALABILITY_FOLLOWUP P07: Track-B Test Packetization

## Objective

- Break the Track-B QML preference and scene-model umbrellas into focused suites plus shared support while keeping the top-level regression entrypoints stable.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet is in progress.

## Execution Dependencies

- `P06`

## Target Subsystems

- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/graph_track_b/scene_and_model.py`
- `tests/graph_track_b/qml_support.py`
- `tests/graph_track_b/theme_support.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`
- `tests/graph_track_b/qml_preference_performance_suite.py`
- `tests/graph_track_b/scene_model_graph_model_suite.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`
- `tests/test_graph_track_b.py`
- `tests/test_flow_edge_labels.py`

## Conservative Write Scope

- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/graph_track_b/scene_and_model.py`
- `tests/graph_track_b/qml_support.py`
- `tests/graph_track_b/theme_support.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`
- `tests/graph_track_b/qml_preference_performance_suite.py`
- `tests/graph_track_b/scene_model_graph_model_suite.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`
- `tests/test_graph_track_b.py`
- `tests/test_flow_edge_labels.py`
- `docs/specs/work_packets/ui_context_scalability_followup/P07_track_b_test_packetization_WRAPUP.md`

## Required Behavior

- Split `tests/graph_track_b/qml_preference_bindings.py` and `tests/graph_track_b/scene_and_model.py` into focused suites with these support files:
  - `qml_support.py`
  - `theme_support.py`
  - `qml_preference_rendering_suite.py`
  - `qml_preference_performance_suite.py`
  - `scene_model_graph_model_suite.py`
  - `scene_model_graph_scene_suite.py`
- Keep `tests/graph_track_b/qml_preference_bindings.py` as the stable regression entrypoint for QML preference coverage.
- Keep `tests/graph_track_b/scene_and_model.py` as the stable regression entrypoint for scene-model coverage.
- End each of those top-level entry files at or below `200` lines.
- Preserve the current regression entry commands and the Track-B rendering, preference, scene-model, and geometry coverage they already prove.
- Update inherited Track-B and edge-label regression anchors in place when suite ownership or shared fixtures move.

## Non-Goals

- No source refactors in this packet.
- No canonical packet-doc updates yet; that belongs to `P08`.
- No new Track-B behavior.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py tests/graph_track_b/scene_and_model.py tests/test_graph_track_b.py tests/test_flow_edge_labels.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py tests/graph_track_b/scene_and_model.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_followup/P07_track_b_test_packetization_WRAPUP.md`
- `tests/graph_track_b/qml_support.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`

## Acceptance Criteria

- The Track-B regression coverage moves into focused suites behind the stable top-level entrypoints.
- `tests/graph_track_b/qml_preference_bindings.py` is at or below `200` lines.
- `tests/graph_track_b/scene_and_model.py` is at or below `200` lines.
- The inherited Track-B regression anchors pass.

## Handoff Notes

- `P08` must update the canonical packet docs so future graph-canvas and edge-related UI work names this regression packet explicitly instead of regrowing the Track-B umbrellas.
