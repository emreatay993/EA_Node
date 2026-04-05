# UI_CONTEXT_SCALABILITY_FOLLOWUP P05: Main Window Bridge Test Packetization

## Objective

- Break the main-window bridge regression umbrella into focused bridge suites plus shared support while keeping the top-level regression entrypoint stable.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet is in progress.

## Execution Dependencies

- `P04`

## Target Subsystems

- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/bridge_contracts_library_and_inspector.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/bridge_contracts_workspace_and_console.py`
- `tests/main_window_shell/bridge_contracts_main_window.py`
- `tests/test_main_window_shell.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/shell_basics_and_search.py`

## Conservative Write Scope

- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/bridge_contracts_library_and_inspector.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/bridge_contracts_workspace_and_console.py`
- `tests/main_window_shell/bridge_contracts_main_window.py`
- `tests/test_main_window_shell.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `docs/specs/work_packets/ui_context_scalability_followup/P05_main_window_bridge_test_packetization_WRAPUP.md`

## Required Behavior

- Split `tests/main_window_shell/bridge_contracts.py` into focused suites with these support files:
  - `bridge_support.py`
  - `bridge_contracts_library_and_inspector.py`
  - `bridge_contracts_graph_canvas.py`
  - `bridge_contracts_workspace_and_console.py`
  - `bridge_contracts_main_window.py`
- Keep `tests/main_window_shell/bridge_contracts.py` as the stable regression entrypoint that aggregates the focused suites.
- End the packet with `tests/main_window_shell/bridge_contracts.py` at or below `150` lines.
- Preserve the current regression entry command and the bridge coverage it already proves.
- Update inherited shell and main-window regression anchors in place when shared fixtures or suite ownership move.

## Non-Goals

- No source refactors in this packet.
- No graph-surface or Track-B regression packetization yet.
- No new bridge behavior.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts.py tests/test_main_window_shell.py tests/test_window_library_inspector.py tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_followup/P05_main_window_bridge_test_packetization_WRAPUP.md`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`

## Acceptance Criteria

- The bridge regression coverage moves into focused suites behind the stable top-level entrypoint.
- `tests/main_window_shell/bridge_contracts.py` is at or below `150` lines.
- The inherited bridge and shell regression anchors pass.

## Handoff Notes

- `P08` must update the canonical packet docs so future shell UI work names this regression packet explicitly instead of growing the bridge umbrella again.
