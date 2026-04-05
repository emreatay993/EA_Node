# UI_CONTEXT_SCALABILITY_FOLLOWUP P04: Graph Scene Mutation Packet Split

## Objective

- Split graph-scene mutation history into focused policy and operation modules while keeping the legacy mutation-history entry surface stable.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet is in progress.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/*.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_main_window_shell.py`
- `tests/test_comment_backdrop_interactions.py`
- `tests/test_comment_backdrop_collapse.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/*.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_main_window_shell.py`
- `tests/test_comment_backdrop_interactions.py`
- `tests/test_comment_backdrop_collapse.py`
- `docs/specs/work_packets/ui_context_scalability_followup/P04_graph_scene_mutation_packet_split_WRAPUP.md`

## Required Behavior

- Create a focused `ea_node_editor/ui_qml/graph_scene_mutation/` package with these modules:
  - `policy.py`
  - `selection_and_scope_ops.py`
  - `clipboard_and_fragment_ops.py`
  - `alignment_and_distribution_ops.py`
  - `grouping_and_subnode_ops.py`
  - `comment_backdrop_ops.py`
- Keep `graph_scene_mutation_history.py` as the stable facade entry surface for existing callers.
- End the packet with `graph_scene_mutation_history.py` at or below `350` lines.
- Preserve current graph-scene bridge, clipboard, alignment, grouping, subnode, scope-navigation, and comment-backdrop behavior.
- Update inherited graph-surface and shell regression anchors in place when packet-owned helper locations or import surfaces move.

## Non-Goals

- No main-window bridge regression-suite split yet; that belongs to `P05`.
- No graph-surface or Track-B regression-suite split yet.
- No new graph-scene features.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py tests/test_main_window_shell.py tests/test_comment_backdrop_interactions.py tests/test_comment_backdrop_collapse.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_comment_backdrop_interactions.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_followup/P04_graph_scene_mutation_packet_split_WRAPUP.md`
- `ea_node_editor/ui_qml/graph_scene_mutation/policy.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/comment_backdrop_ops.py`

## Acceptance Criteria

- The mutation helpers live in focused modules behind the stable facade file.
- `graph_scene_mutation_history.py` is at or below `350` lines.
- The packet-owned graph-scene and comment-backdrop regression anchors pass.

## Handoff Notes

- `P06` may inherit the slimmer graph-scene mutation seams when it packetizes the graph-surface regression umbrellas.
