# DEAD_CODE_HYGIENE P03: Regression Locks

## Objective
- Add or tighten static regression coverage so the removed QML plumbing and removed Python helpers do not silently return, while documenting the intentionally retained compatibility seams in the packet wrap-up and status ledger.

## Preconditions
- `P00` is marked `PASS` in [DEAD_CODE_HYGIENE_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md).
- `P01` and `P02` are marked `PASS`.
- No later `DEAD_CODE_HYGIENE` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`

## Target Subsystems
- `tests/test_main_window_shell.py`
- `tests/test_dead_code_hygiene.py` only if the helper-absence assertions do not fit cleanly into existing tests
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md` for the packet result and retained-compatibility notes only

## Conservative Write Scope
- `tests/test_main_window_shell.py`
- `tests/test_dead_code_hygiene.py`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md`
- `docs/specs/work_packets/dead_code_hygiene/P03_regression_locks_WRAPUP.md`

## Required Behavior
- Prefer extending the existing boundary coverage in `tests/test_main_window_shell.py` so the removed shell-surface property declarations and `MainShell.qml` call-site assignments do not return.
- Freeze the exact `P01` cleanup boundary for:
  - removed `mainWindowRef` property declarations in the packet-owned shell components
  - removed `workspaceTabsBridgeRef` and `consoleBridgeRef` declarations in `WorkspaceCenterPane.qml`
  - removed `MainShell.qml` assignments for those deleted properties
  - continued presence of the retained bridge/context seams that remain intentionally live
- Add a dedicated `tests/test_dead_code_hygiene.py` only if the helper-removal assertions do not fit cleanly into existing tests.
- Freeze the exact `P02` helper boundary so `dict_to_event_type`, `input_port_is_available`, and `inline_body_height` do not silently reappear.
- Rerun the full `P01` and `P02` verification commands, plus any new packet-owned audit test module if added.
- Record the intentionally retained public-looking surfaces and compatibility seams in the packet wrap-up and shared status ledger instead of widening into product-doc churn.

## Non-Goals
- No new runtime cleanup beyond test-only regression locks.
- No product-doc churn in `README.md`, `ARCHITECTURE.md`, requirements specs, or broader traceability docs.
- No widening into unrelated dead-code sweeps or linter cleanup.
- No changes to global context-property names, bridge object names, or selected-node inspector APIs.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.ShellLibraryBridgeQmlBoundaryTests tests.test_main_window_shell.ShellInspectorBridgeQmlBoundaryTests tests.test_main_window_shell.ShellWorkspaceBridgeQmlBoundaryTests tests.test_main_window_shell.GraphCanvasQmlBoundaryTests tests.test_main_window_shell.MainWindowShellContextBootstrapTests -v`
2. `./venv/Scripts/python.exe -m pytest tests/test_icon_registry.py tests/test_window_library_inspector.py tests/test_execution_client.py tests/test_execution_worker.py tests/test_graph_track_b.py -q`
3. `./venv/Scripts/python.exe -m pytest tests/test_dead_code_hygiene.py -q` if this packet adds `tests/test_dead_code_hygiene.py`

## Review Gate
- `git diff --check -- tests/test_main_window_shell.py tests/test_dead_code_hygiene.py`

## Expected Artifacts
- `docs/specs/work_packets/dead_code_hygiene/P03_regression_locks_WRAPUP.md`

## Acceptance Criteria
- The full `P01` verification command passes again.
- The full `P02` verification command passes again.
- Any new packet-owned audit test module passes if it is added.
- The regression coverage freezes the deleted QML plumbing and deleted Python helpers without asserting against intentionally retained compatibility seams that must stay.
- The wrap-up and status ledger explicitly record any intentionally retained public-looking surfaces such as `overlayHostItem` or broader package/public seams that remain out of scope.

## Handoff Notes
- This is the final implementation packet in the set; the wrap-up and status ledger should clearly state whether `overlayHostItem` remained live and which broader unused-tooling findings stayed intentionally out of scope.
- Keep the regression guards static and source-boundary-oriented; do not introduce brittle UI-behavior assertions when simple source-contract locks are sufficient.
