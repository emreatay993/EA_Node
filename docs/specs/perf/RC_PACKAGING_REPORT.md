# RC Packaging Report

- Updated: `2026-03-18`
- Evidence Status: Archived RC packaging smoke snapshot restored from repo
  history after the checked-in report disappeared from the current proof layer.
- Snapshot Date (UTC): `2026-03-01T17:01:38.434491+00:00`
- Snapshot Build Command: `.\scripts\build_windows_package.ps1 -Clean`
- Current Constraint: P08 did not rerun packaging. The historical
  `artifacts\pyinstaller\` bundle referenced by the archived run is not
  retained in this checkout, so rerun packaging before using this as current
  release evidence.

## Archived 2026-03-01 Snapshot

### Build Result

- Status: `PASS`
- Toolchain: `PyInstaller 6.19.0` (venv Python `3.10.0`)
- Executable path: `artifacts\pyinstaller\dist\EA_Node_Editor\EA_Node_Editor.exe`
- Build artifacts root: `artifacts\pyinstaller\`

### Smoke Result

- Status: `PASS`
- Method: offscreen startup (`QT_QPA_PLATFORM=offscreen`) with timed liveness
  check
- Duration: process remained alive for `5` seconds before controlled
  termination
- Result detail: startup completed with no early process exit

## Known Limitations

- Startup smoke test validates process launch and liveness only, not end-user
  interaction flows.
- Offscreen smoke mode does not represent final desktop GPU/compositor
  behavior.
- OneDir packaging does not include installer or signing artifacts in this
  repo snapshot.
- The PyInstaller warning report contains platform-optional modules and
  dependency-gated optional deps (`openpyxl`, `psutil`).
