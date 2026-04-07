# EXECUTION_EDGE_PROGRESS_VISUALIZATION P04: Execution Edge Renderer Highlights

## Objective
- Render dim-before-progress control edges plus the one-shot flash overlay on top of the packet-owned snapshot metadata contract and prove the full shell/QML execution-edge behavior without changing unrelated edge families.

## Preconditions
- `P03` is marked `PASS` in [EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md](./EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md).
- No later `EXECUTION_EDGE_PROGRESS_VISUALIZATION` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
- `tests/test_shell_run_controller.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
- `tests/test_shell_run_controller.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`
- `docs/specs/work_packets/execution_edge_progress_visualization/P04_execution_edge_renderer_highlights_WRAPUP.md`

## Required Behavior
- Update the standard EdgeCanvas paint path so unprogressed execution edges render at `0.35` alpha and `1.7px` base width, while progressed execution edges render at their current normal stroke/color/width.
- Render the first progress flash as a packet-owned overlay that uses the edge's current base color, `+1.4px` width, and alpha easing from `0.55` to `0.0` over `240ms`.
- Respect the packet-owned snapshot contract from `P03`: do not recompute execution progress independently inside `EdgeCanvasLayer`.
- Preserve current selection and preview interaction colors and widths. Selected or previewed execution edges must not be dimmed, but an active flash may still render on top.
- Leave data edges and passive flow edges unchanged.
- Add packet-owned shell/QML regressions whose names include `execution_edge_progress_visualization` so the verification commands below remain stable.
- Cover the end-user behavior in packet-owned tests: control edges start dimmed during an active run, progressed edges return to normal and flash once, failed-branch edges progress through `node_failed_handled`, run completion/stop/fatal failure clear the edge state, and non-control edges stay unchanged.

## Non-Goals
- No new bridge properties or snapshot-field renames.
- No requirement-doc or QA-matrix updates yet.
- No repo-wide renderer restyling outside execution-edge behavior.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k execution_edge_progress_visualization --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py -k execution_edge_progress_visualization --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k execution_edge_progress_visualization --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/execution_edge_progress_visualization/P04_execution_edge_renderer_highlights_WRAPUP.md`

## Acceptance Criteria
- Execution-edge paint output follows the documented dim-before-progress and one-shot flash contract without regressing non-control edges.
- Selected and previewed execution edges are not dimmed, while active flashes may still layer on top.
- The packet-owned `execution_edge_progress_visualization` shell/QML regressions pass, including the handled-failure branch and terminal cleanup paths.

## Handoff Notes
- `P05` should reuse the verification commands from this packet verbatim when it updates the retained QA matrix and traceability evidence.
- Any later packet that needs to change the packet-owned snapshot contract from `P03` must inherit and update the `tests/test_flow_edge_labels.py` regression anchor before changing this renderer packet.
