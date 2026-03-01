# RC Packaging Report

- Date (UTC): `2026-03-01T17:01:38.434491+00:00`
- Build command: `.\scripts\build_windows_package.ps1 -Clean`
- Smoke coverage: packaged executable startup for short-run validation

## Build Result

- Status: `PASS`
- Toolchain: `PyInstaller 6.19.0` (venv Python `3.10.0`)
- Executable path: `artifacts\pyinstaller\dist\EA_Node_Editor\EA_Node_Editor.exe`
- Build artifacts root: `artifacts\pyinstaller\`

## Smoke Result

- Status: `PASS`
- Method: offscreen startup (`QT_QPA_PLATFORM=offscreen`) with timed liveness check
- Duration: process remained alive for `5` seconds before controlled termination
- Result detail: startup completed with no early process exit

## Known Limitations

- Startup smoke test validates process launch/liveness only, not end-user interaction flows.
- Offscreen smoke mode does not represent final desktop compositor/GPU behavior.
- OneDir packaging does not include installer/signing artifacts in this repo.
- PyInstaller warning report contains platform-optional modules and optional deps (`openpyxl`, `psutil`) that are intentionally dependency-gated at runtime.

## RC3 Installer Pipeline Update

- Date (UTC): `2026-03-01T20:21:21Z`
- Installer command: `powershell -NoProfile -File scripts/build_windows_installer.ps1`
- Verification scope: unattended installer bundle generation + install/smoke/uninstall lifecycle validation

### Installer Result

- Status: `PASS`
- Run id: `20260301_232051`
- Bundle root: `artifacts\releases\installer\20260301_232051\`
- Bundle archive: `artifacts\releases\installer\20260301_232051\EA_Node_Editor_installer_bundle_20260301_232051.zip`
- Manifest: `artifacts\releases\installer\20260301_232051\installer_manifest.json`
- Validation report: `artifacts\releases\installer\20260301_232051\installer_validation.json`

### Validation Evidence

- Install phase: `PASS`
- Smoke phase: `PASS` (`5s`, offscreen launch/liveness check)
- Uninstall phase: `PASS`
- Source executable SHA-256: `28818C5CB9161AAFC2D62C824FCF2B2996F54623603C0DFEF967487E01E36277`
- Installer bundle SHA-256: `52CDEDBDCB2E2D003794E90D127C71E472FD5BB0FCB3C3A809DF578703FDB22B`

## RC3 Signing and Verification Update

- Date (UTC): `2026-03-01T20:27:46Z`
- Signing verify command: `powershell -NoProfile -File scripts/sign_release_artifacts.ps1 -VerifyOnly`
- Packaging verify command: `powershell -NoProfile -File scripts/build_windows_package.ps1 -SkipSmoke`

### Signing Result

- Status: `PASS`
- Signing run id: `20260301_232746`
- Signing manifest: `artifacts/releases/signing/20260301_232746/signing_manifest.json`
- Signing summary: `artifacts/releases/signing/20260301_232746/signing_summary.md`
- Mode: `verify_only`
- Require signed artifacts: `False`
- Signable target snapshot: executable/scripts observed as `NotSigned` in verify-only mode (expected without configured cert); strict enforcement remains available via `EA_SIGN_REQUIRE_SIGNED`.
- Supplementary strict-gate check: `EA_SIGN_REQUIRE_SIGNED=1` produced expected non-zero exit (`1`) with evidence at `artifacts/releases/signing/20260301_233011/`.

### Packaging Rebuild Result

- Status: `PASS`
- Rebuilt executable: `artifacts/pyinstaller/dist/EA_Node_Editor/EA_Node_Editor.exe`
- Dependency matrix emission: `docs/specs/perf/rc3/dependency_matrix.csv`
