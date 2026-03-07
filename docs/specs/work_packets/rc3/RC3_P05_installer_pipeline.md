# RC3 P05: Installer Pipeline

## Objective
- Add reproducible installer generation and verification steps for install/uninstall lifecycle validation.

## Non-Objectives
- No replacement of the current PyInstaller OneDir packaging baseline.
- No certificate provisioning automation in this packet.

## Inputs
- `docs/specs/perf/PILOT_BACKLOG.md`
- `docs/PACKAGING_WINDOWS.md`
- `scripts/build_windows_package.ps1`

## Allowed Files
- `scripts/*`
- `docs/PACKAGING_WINDOWS.md`
- `docs/specs/perf/RC_PACKAGING_REPORT.md`
- `docs/specs/perf/rc3/*`

## Do Not Touch
- `ea_node_editor/execution/**`
- `ea_node_editor/persistence/**`

## Verification
1. `powershell -NoProfile -File scripts/build_windows_package.ps1 -SkipSmoke`
2. `powershell -NoProfile -File scripts/build_windows_installer.ps1`

## Output Artifacts
- `artifacts/releases/installer/`
- `docs/specs/perf/rc3/installer_validation.md`

## Merge Gate (Requirement IDs)
- `AC-REQ-QA-001-02`
- `REQ-QA-001`
