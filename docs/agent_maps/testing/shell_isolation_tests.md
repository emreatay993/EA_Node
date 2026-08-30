# Shell Isolation Tests

## Purpose
Use this for shell-backed workflows that need process isolation, shell target catalogs, and main-window shell test routing.

## Start Here
- `tests/test_shell_isolation_phase.py`
- `tests/shell_isolation_runtime.py`
- `tests/main_window_shell/`
- `scripts/verification_manifest.py`

## Common Changes
- Add shell-backed targets to manifest-owned shell isolation catalogs.
- Keep the verified 51-target catalog's split edit/clipboard (18/10/8), seven drop/connect (4/3/7/7/2/1/4), split Media Panel shell coverage (9/10 and 3/2), seven shell-basics, two bridge-local, and split view/library/inspector (7/7/13/14/13) shards disjoint, ordered, and serial inside each child process; pytest nodeid lists pass `-n 0`. The retired `GraphCanvasBridgeTests` nodeid left the existing `main_window__bridge_local_pack__contracts_and_library_qml` pack; the pack itself and the 51-target registry remain.
- Keep the outer full shell-isolation phase at its manifest-owned four-worker cap; each child stays serial.
- Keep catalog-owned Media Panel and graph-host targets free of nested subprocess proxy classes and `load_tests` wrappers.
- Keep shell-isolated direct `unittest` commands as focused manual reruns only.
- Prefer `run_verification.py --mode full` for release confidence when shell-backed behavior changes.
- For shell composition changes, keep `tests/test_main_bootstrap.py`, `tests/test_main_window_shell.py`, and `tests/test_shell_window_lifecycle.py` aligned with the direct `ShellWindow()` and `create_shell_window()` paths.
- Selected-node inspector link action contracts live in `tests/main_window_shell/`; add shell-isolation catalog entries only if future link tests require isolated shell startup.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_shell_isolation_phase.py --ignore=venv -q
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --dry-run
```

## Update Triggers
Update when shell target catalogs, shell runtime helpers, or shell-backed test ownership changes.

## 2026-05-31 Shell Services Bundle Update

- P02 service-bundle coverage lives in `tests/test_main_bootstrap.py`, `tests/test_main_window_shell.py`, `tests/test_shell_window_lifecycle.py`, and the split `tests/main_window_shell/` contracts. These tests assert `window.shell_services`, stable QML context registration, and direct/factory shell lifecycle behavior.

## 2026-05-31 Shell Facade Retirement Update

- P03 coverage in `tests/test_main_bootstrap.py` and `tests/test_main_window_shell.py` asserts that `window_state_helpers.py`, `SHELL_WINDOW_FACADE_BINDINGS`, `WINDOW_STATE_FACADE_BINDINGS`, and `locals().update(...)` class mutation stay retired.

## 2026-06-10 Shell Composition Package Update

- `tests/test_main_window_shell.py` and `tests/test_graph_action_contracts.py` now pin the QML graph-action `request_*` slots to the `window_state.workspace_graph_actions` mixin class body (controller dispatch unchanged), and `tests/test_main_bootstrap.py` asserts controllers/presenters receive the `ShellWindow` directly with no host-adapter layer.
- The shared shell harness (`tests/main_window_shell/base.py`, `tests/test_shell_window_lifecycle.py`) patches `ea_node_editor.ui.shell.composition.controllers._create_shell_execution_client`; bootstrap-internal patch targets live on `ea_node_editor.ui.shell.composition.bootstrap`.

## 2026-05-31 Mutation UI Effects Update

- P08 coverage adds `tests/main_window_shell/mutation_ui_effects.py`, loaded through `tests/test_main_window_shell.py`, to assert explicit shell post-mutation effects without requiring a full shell instance for every effect combination.
