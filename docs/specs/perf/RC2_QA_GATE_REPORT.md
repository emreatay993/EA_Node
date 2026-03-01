# RC2 QA Gate Report

- Generated: `2026-03-01`
- Test command: `venv\Scripts\python -m unittest discover -s tests -v`
- Perf command: `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`

## Summary

| Cluster | Status | Evidence |
|---|---|---|
| Legacy functional suites | PASS | Existing `test_*` suites in `tests/` |
| RC2 shell/theme/settings/editor | PASS | `tests/test_theme_shell_rc2.py`, `tests/test_settings_dialog_rc2.py`, `tests/test_script_editor_dock_rc2.py` |
| RC2 decorator SDK | PASS | `tests/test_decorator_sdk_rc2.py` |
| RC2 process runner + cancellation | PASS | `tests/test_process_run_node_rc2.py` |
| RC2 schema v2 migration | PASS | `tests/test_serializer_v2_migration_rc2.py` |
| Performance gate | PASS | `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` |

## Result

- Total tests: `73`
- Passed: `73`
- Failed: `0`
- Performance thresholds:
  - Pan/Zoom combined p95: `30.222 ms` (`<= 33 ms` target) PASS
  - Load p95: `345.132 ms` (`< 3000 ms` target) PASS

## Notes

- Benchmarks were executed in offscreen Qt mode; interactive desktop runs should be collected separately for pilot hardware baselines.

