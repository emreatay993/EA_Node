# SHELL_MOD P04: Window Search and Scope State Extraction

## Objective
- Extract graph-search state machine, scope-camera state handling, and graph-hint/snap state helpers from `window.py`.

## Preconditions
- `P03` is marked `PASS` in [SHELL_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_search_scope_state.py` (new)
- `tests/test_main_window_shell.py`

## Required Behavior
- Extract logic for:
  - `_set_graph_search_state`, refresh, move/highlight/accept/jump workflow
  - runtime scope camera key/save/restore navigation helpers
  - graph hint state lifecycle
  - snap-to-grid state synchronization with action check state
- Keep all slot/property signatures and behavior stable.

## Non-Goals
- No controller code extraction in this packet.
- No action/menu extraction changes.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell -v`

## Acceptance Criteria
- `window.py` remains the QML slot/property host while extracted helpers own state-transition details.
- Search and scope-related shell tests pass.

## Handoff Notes
- `P05` starts workspace controller decomposition.
