# Main Window Shell Test Packet

Baseline packet: `P05 Main Window Bridge Test Packetization`.

Use this contract when a UI change touches shell bridge exports, bridge-backed library or inspector workflows, workspace or console shell wiring, or the stable main-window regression entrypoints that prove those seams.

## Source Packet Docs

- [Shell Packet](./SHELL_PACKET.md)
- [Presenters Packet](./PRESENTERS_PACKET.md)
- [Graph Scene Packet](./GRAPH_SCENE_PACKET.md)
- [Graph Canvas Packet](./GRAPH_CANVAS_PACKET.md)

## Owner Files

- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/bridge_contracts_library_and_inspector.py`
- `tests/main_window_shell/bridge_contracts_main_window.py`
- `tests/main_window_shell/bridge_contracts_workspace_and_console.py`

## Public Entry Points

- `tests/main_window_shell/bridge_contracts.py` is the stable regression entrypoint and compatibility export surface for bridge-focused coverage.
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`, `tests/main_window_shell/bridge_contracts_library_and_inspector.py`, `tests/main_window_shell/bridge_contracts_main_window.py`, and `tests/main_window_shell/bridge_contracts_workspace_and_console.py` own the detailed bridge suites behind that entrypoint.

## State Owner

- `tests/main_window_shell/bridge_support.py` owns the shared shell harness, named-child lookup helpers, and direct-env constants reused across the focused suites.
- The focused suite modules own detailed bridge assertions; `tests/main_window_shell/bridge_contracts.py` only aggregates and re-exports them.

## Allowed Dependencies

- This regression packet may depend on the public bridge and helper seams documented in the linked source packet docs.
- This regression packet may reuse shared shell test harnesses under `tests/main_window_shell/` when they remain import surfaces rather than local umbrella bodies.
- Higher-level shell regression anchors such as `tests/test_main_window_shell.py` and `tests/test_window_library_inspector.py` may inherit this packet's helpers, but packet-owned bridge assertions stay here first.

## Invariants

- `tests/main_window_shell/bridge_contracts.py` stays thin and import-compatible for packet-external callers.
- Shared bridge harness helpers stay centralized in `tests/main_window_shell/bridge_support.py`.
- Detailed bridge coverage stays in the focused suite modules instead of regrowing inside `tests/main_window_shell/bridge_contracts.py` or `tests/test_main_window_shell.py`.
- When a bridge export or helper moves, the aggregator exports and the focused suites update together.

## Forbidden Shortcuts

- Do not regrow `tests/main_window_shell/bridge_contracts.py` into a local umbrella body.
- Do not duplicate shell harness setup or named-child helper logic across the focused suite modules.
- Do not move packet-owned bridge assertions back into generic shell tests when the focused bridge suites can carry the proof.

## Required Tests

- `tests/main_window_shell/bridge_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
