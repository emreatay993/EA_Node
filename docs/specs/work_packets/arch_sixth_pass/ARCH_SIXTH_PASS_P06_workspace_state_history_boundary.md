# ARCH_SIXTH_PASS P06: Workspace State And History Boundary

## Objective
- Separate undo, clipboard, and persistence-facing workspace state from live authoring orchestration so overlay docs, scene refresh, and history restore stop leaking through unrelated graph and shell layers.

## Preconditions
- `P00` through `P05` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- workspace history snapshots
- clipboard fragment and style codecs
- live workspace state adapters

## Conservative Write Scope
- `ea_node_editor/ui/shell/runtime_history.py`
- `ea_node_editor/ui/shell/runtime_clipboard.py`
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `tests/test_graph_track_b.py`
- `tests/test_serializer.py`
- `tests/test_passive_runtime_wiring.py`
- `docs/specs/work_packets/arch_sixth_pass/P06_workspace_state_history_boundary_WRAPUP.md`

## Required Behavior
- Move packet-owned fragment and style codec ownership out of shell-only helpers when a graph-owned or workspace-state-owned module is more appropriate.
- Introduce a clearer adapter for workspace snapshot and restore behavior so scene refresh and persistence overlay details are not spread across unrelated layers.
- Reduce direct live-model mutation of persistence-only or history-only details in packet-owned flows.
- Preserve undo/redo behavior, clipboard flows, fragment paste behavior, and persisted project compatibility exactly.

## Non-Goals
- No workspace ordering or lifecycle authority changes in this packet.
- No runtime execution boundary changes in this packet.
- No plugin/package work in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py tests/test_serializer.py tests/test_passive_runtime_wiring.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py -q -k "RuntimeGraphHistoryTrackBTests"`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P06_workspace_state_history_boundary_WRAPUP.md`

## Acceptance Criteria
- Packet-owned history and clipboard flows rely on a clearer workspace-state boundary than the current mix of shell, graph, and persistence helpers.
- Undo, clipboard, and serializer regressions pass with unchanged behavior.
- The packet leaves workspace lifecycle policy for `P07`.

## Handoff Notes
- `P07` owns workspace lifecycle authority after the packet-owned state/history seams are clearer.
- Preserve current clipboard and snapshot semantics exactly.
