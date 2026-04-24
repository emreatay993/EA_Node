# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P07: QML Graph Canvas Core

## Objective

Make the graph canvas a feature-owned QML port boundary: canvas roots route actions and state, while leaf graph-canvas components stop mixing scene, shell, viewer, fullscreen, and fallback bridge behavior.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and graph-canvas/QML tests needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P06_qml_shell_roots` is `PASS`.

## Execution Dependencies

- `P06_qml_shell_roots`

## Target Subsystems

- GraphCanvas feature root and graph-canvas components
- Graph scene bridges and payload builders
- Graph action contracts
- Graph-surface input tests

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/**`
- `ea_node_editor/ui_qml/graph_scene/**`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/**`
- `ea_node_editor/ui_qml/graph_action_bridge.py`
- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_comment_backdrop_contracts.py`
- `tests/test_passive_runtime_wiring.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P07_qml_graph_canvas_core_WRAPUP.md`

## Required Behavior

- Keep `GraphCanvas.qml` as the graph feature root.
- Keep `GraphCanvasRootBindings.qml` as the QML-facing canvas port facade.
- Move fallback bridge lookups and raw action-id switching toward semantic handlers or typed action descriptors owned by feature roots.
- Preserve selection, drag, resize, wire creation, quick insert, context menu, and graph action behavior.

## Non-Goals

- Do not move passive media/viewer overlay policy; that is `P08`.
- Do not restructure shell-level `MainShell.qml`; that is `P06`.
- Do not change backend graph mutation semantics unless QML bridge contracts require an adapter.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_comment_backdrop_contracts.py tests/test_passive_runtime_wiring.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P07_qml_graph_canvas_core_WRAPUP.md`

## Acceptance Criteria

- Graph canvas components have clearer routing and port ownership.
- Existing graph-canvas behavior remains compatible.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If this packet discovers unavoidable viewer/fullscreen changes, stop at a thin compatibility adapter and hand the deeper work to `P08`.
