# Track H QA Gate Report

- Generated: `2026-03-01`
- Test command: `venv\Scripts\python -m unittest discover -s tests -v`
- Benchmark command: `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`

## Gate Summary

| Requirement Cluster | Status | Evidence |
|---|---|---|
| Architecture + UI shell/workspace behavior | PASS | `tests/test_main_window_shell.py`, `tests/test_workspace_manager.py` |
| Graph model + interaction behavior | PASS | `tests/test_graph_track_b.py` |
| Node SDK + registry correctness | PASS | `tests/test_registry_filters.py`, `tests/test_registry_validation.py`, `tests/test_inspector_reflection.py` |
| Execution engine + failure handling | PASS | `tests/test_execution_worker.py`, `tests/test_execution_client.py`, `tests/test_main_window_shell.py` (`test_run_failed_event_centers_failed_node_and_reports_exception_details`) |
| Persistence + session lifecycle | PASS | `tests/test_serializer.py`, `tests/test_main_window_shell.py` |
| Integration smoke flows | PASS | `tests/test_integrations_track_f.py` |
| Performance gate (target-scale load + pan/zoom) | PASS | `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` (load p95 `213.564 ms`, pan p95 `15.183 ms`, zoom p95 `22.468 ms`) |

## Execution Result

- Full suite: `57/57` tests passed.
- Benchmark requirement checks: `REQ-PERF-001` PASS, `REQ-PERF-002` PASS, `REQ-PERF-003` PASS.

## Environment Limitations

- Benchmark timings were collected with `QT_QPA_PLATFORM=offscreen`.
- Offscreen timings are suitable for regression gating in this environment, but absolute numbers can differ on interactive desktop/GPU setups.

