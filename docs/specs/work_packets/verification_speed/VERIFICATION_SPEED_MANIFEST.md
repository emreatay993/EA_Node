# VERIFICATION_SPEED Work Packet Manifest

- Date: `2026-03-17`
- Scope baseline: speed up repo verification loops without weakening the current fresh-process shell isolation model, while keeping runtime behavior and accepted QA coverage stable.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [Performance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/80_PERFORMANCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest -q --durations=30` currently takes about `193.88s` on this machine for `450` collected tests, with the slowest cases concentrated in full-shell/QML scenarios.
  - `tests/test_main_window_shell.py` alone currently takes about `100.12s`, and `tests/test_shell_project_session_controller.py` takes about `25.11s`.
  - A fresh `ShellWindow()` currently costs about `870ms` on this machine, and cProfile shows the dominant startup cost is QML shell loading through `QQuickWidget.setSource(...)`, not registry bootstrap.
  - The repo already declares `pytest-xdist` in `pyproject.toml` and `requirements.txt`, but it is not installed in the current project venv; any new runner must retain a serial fallback.
  - `README.md` and `docs/GETTING_STARTED.md` still recommend `unittest discover` as the default day-to-day command even though the repo already carries pytest configuration, `tests/conftest.py`, and heavy shell wrapper modules that need explicit handling.
  - Baseline regression note: `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -k passive_image_panel_properties_and_size -q` currently fails because passive image-panel round-trips add default crop fields. This packet set must treat that persistence failure as out-of-scope baseline context unless a packet explicitly widens into serializer repair.

## Packet Order (Strict)

1. `VERIFICATION_SPEED_P00_bootstrap.md`
2. `VERIFICATION_SPEED_P01_pytest_selection_classification.md`
3. `VERIFICATION_SPEED_P02_shell_wrapper_collection_hygiene.md`
4. `VERIFICATION_SPEED_P03_hybrid_verification_runner.md`
5. `VERIFICATION_SPEED_P04_gui_wait_helper_cleanup.md`
6. `VERIFICATION_SPEED_P05_docs_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/verification-speed/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Pytest Selection Classification | `codex/verification-speed/p01-pytest-selection-classification` | Centralize `gui`/`slow` classification so pytest can split fast, GUI, and slow phases without changing product code |
| P02 Shell Wrapper Collection Hygiene | `codex/verification-speed/p02-shell-wrapper-collection-hygiene` | Stop pytest from directly collecting internal shell-wrapper helper classes while preserving `unittest` isolation flows |
| P03 Hybrid Verification Runner | `codex/verification-speed/p03-hybrid-verification-runner` | Add a repo-owned verification runner with `fast`, `gui`, `slow`, and `full` modes plus serial fallback when `xdist` is unavailable |
| P04 GUI Wait Helper Cleanup | `codex/verification-speed/p04-gui-wait-helper-cleanup` | Replace fixed sleeps in the slow GUI tests with shared event-pumped wait helpers |
| P05 Docs Traceability | `codex/verification-speed/p05-docs-traceability` | Publish the new verification workflow, QA matrix, and traceability updates without loosening shell isolation requirements |

## Locked Defaults

- Preserve the current fresh-process shell isolation model for:
  - `tests.test_main_window_shell`
  - `tests.test_script_editor_dock`
  - `tests.test_shell_run_controller`
  - `tests.test_shell_project_session_controller`
- Do not introduce shared `ShellWindow()` reuse across test methods or packets.
- Treat pytest as the developer-oriented fast-path runner, but keep the isolated shell modules on explicit `unittest` execution in the final `full` workflow.
- Keep the existing `gui` and `slow` marker names from `pyproject.toml`; do not rename them or add alternate equivalents.
- Use `./venv/Scripts/python.exe` for verification commands unless a packet explicitly requires something else.
- Set `QT_QPA_PLATFORM=offscreen` for GUI/QML verification phases and keep serial fallback behavior when `pytest-xdist` is not installed.
- Do not fold the baseline serializer crop-field failure into this packet set unless a packet explicitly widens into persistence repair.
- Prefer test-runner, harness, and documentation changes over production runtime changes. No packet in this set should modify `ea_node_editor/**`.

## Execution Waves

### Wave 1
- `P01`
- `P02`

### Wave 2
- `P03`
- `P04`

### Wave 3
- `P05`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `VERIFICATION_SPEED_Pxx_<name>.md`
- Implementation prompt: `VERIFICATION_SPEED_Pxx_<name>_PROMPT.md`
- Status ledger update in [VERIFICATION_SPEED_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement VERIFICATION_SPEED_PXX_<name>.md exactly. Before editing, read VERIFICATION_SPEED_MANIFEST.md, VERIFICATION_SPEED_STATUS.md, and VERIFICATION_SPEED_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve the current shell-isolation defaults unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update VERIFICATION_SPEED_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P05` may change test/docs/script files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Keep the current shell wrapper load-tests strategy unless a packet explicitly changes it.
- Keep the new runner public mode names stable once `P03` lands: `fast`, `gui`, `slow`, and `full`.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
