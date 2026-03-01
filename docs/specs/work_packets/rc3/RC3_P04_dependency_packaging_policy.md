# RC3 P04: Optional Dependency Packaging Policy

## Objective
- Define and enforce deterministic behavior for optional dependencies (`openpyxl`, `psutil`) across source and packaged runtime modes.

## Non-Objectives
- No addition of new integration node categories.
- No hard requirement that optional packages are always bundled.

## Inputs
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/PACKAGING_WINDOWS.md`
- `docs/specs/perf/PILOT_BACKLOG.md`

## Allowed Files
- `docs/PACKAGING_WINDOWS.md`
- `scripts/build_windows_package.ps1`
- `ea_node_editor/nodes/builtins/integrations.py`
- `tests/test_integrations_track_f.py`
- `docs/specs/perf/rc3/*`

## Do Not Touch
- `ea_node_editor/graph/**`
- `ea_node_editor/workspace/**`

## Verification
1. `venv\Scripts\python -m unittest tests.test_integrations_track_f -v`
2. `powershell -NoProfile -File scripts/build_windows_package.ps1 -SkipSmoke`

## Output Artifacts
- `docs/specs/perf/rc3/dependency_packaging_policy.md`
- `docs/specs/perf/rc3/dependency_matrix.csv`

## Merge Gate (Requirement IDs)
- `REQ-INT-003`
- `REQ-INT-004`
- `REQ-INT-005`
- `AC-REQ-QA-001-02`
