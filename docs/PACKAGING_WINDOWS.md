# Windows Packaging Guide (PyInstaller)

This project ships a Windows package using PyInstaller and the repository-root spec file `ea_node_editor.spec`.

## Prerequisites

- Virtualenv exists at `venv\`.
- Build dependency installed: `venv\Scripts\python -m pip install pyinstaller`.

## Build Command

```powershell
.\scripts\build_windows_package.ps1 -Clean
```

## Optional Flags

- `-SkipSmoke`: build only, no startup smoke check.
- `-SmokeSeconds <int>`: startup smoke duration in seconds (default `5`).

## Output Folder Conventions

- `artifacts\pyinstaller\build\`:
  PyInstaller work files (safe to delete).
- `artifacts\pyinstaller\dist\EA_Node_Editor\`:
  distributable onedir package.
- `artifacts\pyinstaller\dist\EA_Node_Editor\EA_Node_Editor.exe`:
  packaged desktop executable.
- `ea_node_editor.spec`:
  repository-root PyInstaller build configuration used by the script.

## Smoke Test Command

The build script runs an automated startup smoke test by default:

1. sets `QT_QPA_PLATFORM=offscreen`,
2. launches `EA_Node_Editor.exe`,
3. waits for the configured short duration,
4. fails if process exits early,
5. terminates the process after successful startup verification.

Manual smoke run:

```powershell
.\scripts\build_windows_package.ps1 -SmokeSeconds 8
```

## Notes

- The onedir output is preferred for RC reliability and simpler diagnostics.
- If optional dependency `openpyxl` is not installed, Excel XLSX node paths remain dependency-gated at runtime (existing behavior).
