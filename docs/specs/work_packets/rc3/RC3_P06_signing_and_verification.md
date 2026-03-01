# RC3 P06: Signing and Verification

## Objective
- Integrate executable and installer signing verification steps into release flow with explicit fail-fast checks.

## Non-Objectives
- No storage of private signing material in repository.
- No OS policy bypasses for signature trust.

## Inputs
- `docs/specs/perf/PILOT_BACKLOG.md`
- `docs/PACKAGING_WINDOWS.md`
- `docs/specs/perf/RC_PACKAGING_REPORT.md`

## Allowed Files
- `scripts/*`
- `docs/PACKAGING_WINDOWS.md`
- `docs/specs/perf/RC_PACKAGING_REPORT.md`
- `docs/specs/perf/rc3/*`

## Do Not Touch
- `ea_node_editor/graph/**`
- `ea_node_editor/ui/**`

## Verification
1. `powershell -NoProfile -File scripts/sign_release_artifacts.ps1 -VerifyOnly`
2. `powershell -NoProfile -File scripts/build_windows_package.ps1 -SkipSmoke`

## Output Artifacts
- `docs/specs/perf/rc3/signing_verification.md`
- `artifacts/releases/signing/`

## Merge Gate (Requirement IDs)
- `AC-REQ-QA-001-02`
- `REQ-QA-001`
- `REQ-QA-002`
