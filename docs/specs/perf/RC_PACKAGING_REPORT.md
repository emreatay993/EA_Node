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
