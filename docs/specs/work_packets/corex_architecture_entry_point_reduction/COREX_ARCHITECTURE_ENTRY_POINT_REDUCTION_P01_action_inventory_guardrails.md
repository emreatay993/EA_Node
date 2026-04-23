# COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION P01: Action Inventory Guardrails

## Packet Metadata

- Packet: `P01`
- Title: `Action Inventory Guardrails`
- Execution Dependencies: `none`
- Worker model: `gpt-5.5`
- Worker reasoning effort: `xhigh`

## Objective

- Create the canonical graph action contract and static guardrails before any behavior routes move.
- Make future action work start from one inventory instead of searching through PyQt actions, shell slot wrappers, QML menu literals, and command bridge methods.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only source files needed for the action inventory and tests

## Preconditions

- `P00` is complete and the packet docs are available on the target merge branch.
- Existing graph action behavior is unchanged at packet start.

## Execution Dependencies

- none

## Target Subsystems

- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state/workspace_graph_actions.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `tests/test_graph_action_contracts.py`

## Conservative Write Scope

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P01_action_inventory_guardrails_WRAPUP.md`
- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `tests/test_graph_action_contracts.py`

## Required Behavior

- Add `ea_node_editor/ui/shell/graph_action_contracts.py`.
- Define a canonical string-based `GraphActionId` surface for high-level graph UI actions currently exposed through menus, shortcuts, node context menus, edge context menus, selection context menus, and node delegate action requests.
- Add `GraphActionSpec` records with at least:
  - action id
  - label text when user-visible
  - shortcut text when user-visible
  - menu or surface scope
  - destructive flag
  - required payload keys
  - legacy route names that still exist before later packets remove them
- Cover these initial action families:
  - selection editing: duplicate, copy, cut, paste, delete
  - comment and grouping: wrap selection in comment backdrop, group selection, ungroup selection, ungroup node
  - layout: align left/right/top/bottom, distribute horizontal/vertical
  - node operations: remove node, rename node, edit/reset/copy/paste passive node style, open subnode scope, publish custom workflow from node, open comment peek, close comment peek
  - edge operations: remove edge, edit flow edge style, edit flow edge label, reset/copy/paste flow edge style
  - navigation: navigate scope parent, navigate scope root
- Add tests that statically verify every action id literal in `GraphCanvasContextMenus.qml` and `GraphCanvasNodeDelegate.qml` is represented by the contract or is explicitly listed as a low-level non-action exception.
- Add tests that verify PyQt menu labels and shortcut strings for graph actions are represented by the contract.
- Keep this packet inventory-only. It must not change runtime routing behavior.

## Non-Goals

- Do not add `GraphActionController` or `GraphActionBridge`; `P02` owns them.
- Do not rewire PyQt actions; `P03` owns that.
- Do not rewire QML menus or node delegates; `P04` owns that.
- Do not remove legacy methods, QML slots, or shell wrappers.

## Verification Commands

1. Full packet verification:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P01_action_inventory_guardrails_WRAPUP.md`
- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `tests/test_graph_action_contracts.py`

## Acceptance Criteria

- The graph action contract is the only new source of action ids/spec metadata.
- Static tests fail if a QML high-level action literal is added without updating the contract.
- Static tests fail if a graph PyQt action label/shortcut in the current shell action declarations is missing from the contract.
- Runtime behavior is unchanged.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- `P02` must use this contract when building `GraphActionController` and `GraphActionBridge`.
- If `P02` needs to adjust payload keys or legacy route names, it inherits and updates `tests/test_graph_action_contracts.py`.
