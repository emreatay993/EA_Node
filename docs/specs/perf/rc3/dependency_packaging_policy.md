# RC3 Optional Dependency Packaging Policy

- Packet: `RC3-P04`
- Date: `2026-03-01`
- Branch label: `rc3/p04-dependency-packaging-policy`

## Objective Coverage

This packet establishes deterministic optional dependency behavior for `openpyxl` and `psutil` across source and packaged modes, and records packaging-time dependency evidence.

## Runtime Policy

- `openpyxl`:
  - `io.excel_read` / `io.excel_write` continue to support CSV without optional dependencies.
  - XLSX flows require `openpyxl` and now emit deterministic runtime guidance with explicit runtime mode (`source` vs `packaged`).
- `psutil`:
  - System metrics remain optional and deterministic:
    - available: live CPU/RAM metrics,
    - unavailable: `CPU:0% RAM:0/0 GB` fallback.

## Packaging Policy

- Packaging remains non-interactive and CI-friendly.
- `scripts/build_windows_package.ps1` now emits:
  - `docs/specs/perf/rc3/dependency_matrix.csv`
- Matrix rows document:
  - build-env availability,
  - source runtime behavior,
  - packaged runtime behavior,
  - packaging inclusion policy,
  - operator action.

## Verification Commands

1. `venv\Scripts\python -m unittest tests.test_integrations_track_f -v`
2. `powershell -NoProfile -File scripts/build_windows_package.ps1 -SkipSmoke`

## Verification Summary

- Integration suite: **PASS** (`10/10`)
- Packaging build: **PASS** (PyInstaller build complete, smoke skipped by request)
- Dependency matrix emission: **PASS** (`docs/specs/perf/rc3/dependency_matrix.csv` created)

## Requirement Mapping

- `REQ-INT-003`: Excel read/write dependency-gated behavior maintained and clarified.
- `REQ-INT-004`: File IO behavior unchanged and validated by regression suite.
- `REQ-INT-005`: Email behavior unchanged and validated by regression suite.
- `AC-REQ-QA-001-02`: Packaging command remains executable and produces deterministic operator evidence.

## Artifacts

- `docs/specs/perf/rc3/dependency_packaging_policy.md`
- `docs/specs/perf/rc3/dependency_matrix.csv`
