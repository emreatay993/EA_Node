# UI_CONTEXT_SCALABILITY_REFACTOR P01: Shell Window Facade Collapse

## Objective

- Reduce `ShellWindow` to lifecycle, Qt ownership, context-property attachment, and final signal wiring so packet-owned search, graphics-preference, and menu or action helper logic no longer accumulates inside `window.py`.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_REFACTOR` packet is in progress.

## Execution Dependencies

- `P00`

## Target Subsystems

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state_helpers.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_window_lifecycle.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_contracts.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state_helpers.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_window_lifecycle.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_contracts.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P01_shell_window_facade_collapse_WRAPUP.md`

## Required Behavior

- Extract packet-owned menu or action construction into `window_actions.py`.
- Extract packet-owned graph-search, quick-insert, hint, and graphics-preference helper logic into `window_state_helpers.py`.
- Keep `window.py` responsible for `ShellWindow`, Qt lifecycle, top-level widget ownership, context-property export, and final signal wiring only.
- Update inherited shell bootstrap and host regression anchors in place when packet-owned host seams change.
- End the packet with `ea_node_editor/ui/shell/window.py` at or below `900` lines.

## Non-Goals

- No presenter package split yet; that belongs to `P02`.
- No graph-scene, graph-canvas, or edge-rendering packetization yet.
- No new user-facing shell behavior.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/test_shell_window_lifecycle.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_contracts.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_refactor/P01_shell_window_facade_collapse_WRAPUP.md`

## Acceptance Criteria

- `ShellWindow` is no longer the packet-owned workflow bucket for menu construction, graph search, quick insert, or graphics-preference helpers.
- `window.py` stays at or below `900` lines.
- The inherited shell bootstrap, lifecycle, and host regression anchors pass.

## Handoff Notes

- `P02` splits presenters on top of the slimmer shell host surface from this packet.
