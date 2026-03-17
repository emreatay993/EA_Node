# P01 Pytest Selection Classification Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/verification-speed/p01-pytest-selection-classification`
- Commit Owner: `worker`
- Commit SHA: `2384ceea00b5461864b37537a934959d4c3322cc`
- Changed Files: `tests/conftest.py`
- Artifacts Produced: `docs/specs/work_packets/verification_speed/P01_pytest_selection_classification_WRAPUP.md`

Added a centralized `pytest_collection_modifyitems` hook in `tests/conftest.py` that applies path-based `gui` and `slow` markers during collection. The existing session-scoped `QApplication` fixture and `ShellTestEnvironment` helper remain unchanged.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_work_packet_runner.py --collect-only -q -m "not gui and not slow"`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_theme.py tests/test_passive_graph_surface_host.py --collect-only -q -m gui`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py --collect-only -q -m slow`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_theme.py tests/test_passive_graph_surface_host.py --collect-only -q -m gui`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: stay on `codex/verification-speed/p01-pytest-selection-classification`, export `QT_QPA_PLATFORM=offscreen`, and use `./venv/Scripts/python.exe`.
- Action: run `./venv/Scripts/python.exe -m pytest tests/test_work_packet_runner.py --collect-only -q -m "not gui and not slow"`.
- Expected result: pytest only collects `tests/test_work_packet_runner.py` items and reports `7 tests collected`.
- Action: run `./venv/Scripts/python.exe -m pytest tests/test_shell_theme.py tests/test_passive_graph_surface_host.py --collect-only -q -m gui`.
- Expected result: pytest only collects tests from those two GUI modules and reports `21 tests collected`.
- Action: run `./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py --collect-only -q -m slow`.
- Expected result: pytest only collects the Track H harness tests and reports `4 tests collected`.

## Residual Risks

- Newly added Qt/QML-bearing test modules will remain in the fast pytest phase until their paths are added to the centralized GUI classification list.
- The packet verification commands validated representative GUI and slow selection, but they did not directly exercise the four shell-wrapper modules that are also classified as `gui`; P02 and P03 will cover those paths more directly.

## Ready for Integration

- Yes: the centralized marker hook is in place, the packet verification commands pass with the project venv, and the change stays within the packet-owned scope plus the wrap-up artifact.
