# NODE_EXECUTION_VISUALIZATION P03: Node Chrome Execution Highlights

## Objective
- Render running/completed node chrome, timer, and failure-priority behavior on the packet-owned canvas contracts while preserving host render-activation, stacking, and existing chrome/shadow cache stability.

## Preconditions
- `P02` is marked `PASS` in [NODE_EXECUTION_VISUALIZATION_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_STATUS.md).
- No later `NODE_EXECUTION_VISUALIZATION` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeChromeBackground.qml`
- `tests/test_shell_run_controller.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeChromeBackground.qml`
- `tests/test_shell_run_controller.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/node_execution_visualization/P03_node_chrome_execution_highlights_WRAPUP.md`

## Required Behavior
- Consume the packet-owned canvas execution properties in `GraphNodeHost.qml` to derive `isRunningNode`, `isCompletedNode`, render-activation exceptions, and z-priority without mutating stored node geometry.
- Add packet-owned running/completed theme colors and chrome styling consistent with the visual reference and locked defaults.
- Extend `GraphNodeChromeBackground.qml` with a running pulse, completed flash, and failure-priority border logic while preserving packet-owned failure behavior and existing background/chrome cache contracts.
- Add a QML-local elapsed timer below running nodes driven by `isRunningNode` transitions; do not add Python-side timestamp bridging.
- Preserve failure priority over running/completed chrome, and keep completed nodes visibly completed until the run ends.
- Add packet-owned regression tests whose names include `node_execution_visualization` so the targeted verification commands below remain valid across `tests/test_shell_run_controller.py`, `tests/test_passive_graph_surface_host.py`, and `tests/graph_track_b/qml_preference_bindings.py`.
- Keep new QML object names stable when packet-owned probes need them for visibility/property assertions.

## Non-Goals
- No bridge/property renames from `P01` or `P02`.
- No worker protocol, persistence, or execution payload changes.
- No spec-pack, QA-matrix, or traceability updates yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k node_execution_visualization --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py -k node_execution_visualization --ignore=venv -q`
3. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py -k node_execution_visualization --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k node_execution_visualization --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/node_execution_visualization/P03_node_chrome_execution_highlights_WRAPUP.md`

## Acceptance Criteria
- Running nodes pulse blue, show the packet-owned elapsed timer, and stay render-active while executing.
- Completed nodes flash green, then keep a static green border until the run ends.
- Failure red remains the highest-priority visual state over running/completed chrome.
- The packet-owned `node_execution_visualization` integration/probe tests pass without regressing chrome/shadow cache stability.

## Handoff Notes
- `P04` should treat the visual/state behavior implemented here as the shipped baseline for QA and traceability evidence.
- Any later packet that changes timer semantics, object names used by the probes, or failure-vs-running priority must inherit and update the packet-owned test anchors in this packet's scope.
