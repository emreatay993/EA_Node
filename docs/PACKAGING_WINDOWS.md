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
- `-DependencyMatrixPath <path>`: output path for optional dependency policy matrix (default `docs\specs\perf\rc3\dependency_matrix.csv`).

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

## Optional Dependency Policy

The packaging script now emits a deterministic dependency matrix CSV on each build run:

- `docs\specs\perf\rc3\dependency_matrix.csv`

Current optional dependency contract:

- `openpyxl`:
  - Source runtime: CSV flows are always supported; XLSX flows require `openpyxl`.
  - Packaged runtime: same behavior, with deterministic runtime guidance to rebuild package with `openpyxl` in build environment.
  - Policy: optional include, bundle only when installed in build environment.
- `psutil`:
  - Source runtime: live system metrics use `psutil` when available.
  - Packaged runtime: same fallback contract; when unavailable, metrics deterministically show `CPU:0% RAM:0/0 GB`.
  - Policy: optional include, absence allowed with deterministic fallback.

Recommended packaging command for policy evidence:

```powershell
.\scripts\build_windows_package.ps1 -SkipSmoke -DependencyMatrixPath docs\specs\perf\rc3\dependency_matrix.csv
```

## Installer Pipeline (RC3)

Generate unattended installer bundle artifacts and validate install/uninstall lifecycle:

```powershell
.\scripts\build_windows_installer.ps1
```

Installer outputs are written under:

- `artifacts\releases\installer\<run_id>\`
  - `EA_Node_Editor_installer_bundle_<run_id>.zip`
  - `scripts\Install-EA_Node_Editor.ps1`
  - `scripts\Uninstall-EA_Node_Editor.ps1`
  - `installer_manifest.json`
  - `installer_validation.json`

Validation performed by the installer script:

1. Install payload to a temporary target root.
2. Verify installed `EA_Node_Editor.exe` exists.
3. Launch installed executable in `QT_QPA_PLATFORM=offscreen` mode for short liveness check.
4. Execute uninstall and verify executable removal.

The existing OneDir output remains the fallback distribution path.

## Signing and Verification (RC3)

Validate signing metadata for release artifacts:

```powershell
.\scripts\sign_release_artifacts.ps1 -VerifyOnly
```

Sign then verify signable targets (certificate material is externalized):

```powershell
.\scripts\sign_release_artifacts.ps1 -CertThumbprint <thumbprint> -TimestampServer <url> -RequireSignedArtifacts
```

Environment variable equivalents:

- `EA_SIGN_CERT_THUMBPRINT`: signing certificate thumbprint (no private key material stored in repo).
- `EA_SIGN_TIMESTAMP_URL`: RFC3161/AuthentiCode timestamp URL.
- `EA_SIGN_REQUIRE_SIGNED`: strict validation gate (`1|true|yes`) for signable artifacts.

Signing evidence outputs:

- `artifacts\releases\signing\<run_id>\signing_manifest.json`
- `artifacts\releases\signing\<run_id>\signing_summary.md`

Validation behavior:

1. Collect signature snapshots for packaged executable and latest installer scripts.
2. Optionally apply signatures when certificate thumbprint is supplied.
3. Fail fast with non-zero exit when missing artifacts are detected or strict signature verification fails.
