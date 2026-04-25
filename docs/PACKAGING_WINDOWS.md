# Windows Packaging Guide

This repository ships Windows release artifacts from the repository-root
PyInstaller spec file `ea_node_editor.spec`. The active release flow is
profile-aware: `base` is the default packaged app, and `viewer` adds the
optional PyDPF/PyVista runtime stack.

## Prerequisites

- Use the project venv at `venv\`.
- Base profile: install `.[dev]` or at minimum `pyinstaller` in that venv.
- Viewer profile: install `.[ansys,viewer]` or `.[dev]` in that venv before
  packaging.
- If the icon assets change, regenerate the committed SVG/PNG/ICO set first:
  `.\venv\Scripts\python.exe .\scripts\generate_app_icons.py`

## Build Commands

Base package with the default startup smoke check:

```powershell
.\scripts\build_windows_package.ps1 -PackageProfile base -Clean
```

Use this as the default Windows packaging command. A successful run builds the
`COREX_Node_Editor.exe` folder payload and then performs a 5-second offscreen
startup smoke check against the packaged executable. Treat a smoke-test failure
as a broken packaged app, not as a successful build.

Viewer-enabled package without the startup smoke check:

```powershell
.\scripts\build_windows_package.ps1 -PackageProfile viewer -Clean -SkipSmoke
```

Useful flags:

- `-SkipSmoke`: build only, no startup smoke check.
- `-SmokeSeconds <int>`: startup smoke duration in seconds (default `5`).
- `-DependencyMatrixPath <path>`: override the generated dependency policy CSV.
  The default path is `artifacts\releases\packaging\<profile>\dependency_matrix.csv`.

## Output Paths

- PyInstaller build cache: `artifacts\pyinstaller\build\<profile>\`
- PyInstaller dist root: `artifacts\pyinstaller\dist\<profile>\COREX_Node_Editor\`
- Base executable: `artifacts\pyinstaller\dist\base\COREX_Node_Editor\COREX_Node_Editor.exe`
- Viewer executable: `artifacts\pyinstaller\dist\viewer\COREX_Node_Editor\COREX_Node_Editor.exe`
- Dependency matrix CSV: `artifacts\releases\packaging\<profile>\dependency_matrix.csv`

The build script sets `EA_NODE_EDITOR_PACKAGE_PROFILE` for the PyInstaller run,
verifies the expected executable exists, and by default launches it under
`QT_QPA_PLATFORM=offscreen` for a short liveness smoke test.

The PyInstaller output is a folder payload, not a single self-contained `.exe`.
Keep `COREX_Node_Editor.exe` next to its `_internal\` directory and launch it
from the generated `COREX_Node_Editor\` folder.

Open the packaged app directly from the repo root with:

```powershell
& .\artifacts\pyinstaller\dist\base\COREX_Node_Editor\COREX_Node_Editor.exe
```

## Installer Pipeline

Generate and validate an installer bundle from an existing dist folder:

```powershell
.\scripts\build_windows_installer.ps1 -PackageProfile base
```

Viewer installer bundle from the viewer dist output:

```powershell
.\scripts\build_windows_installer.ps1 -PackageProfile viewer
```

Installer outputs are written under `artifacts\releases\installer\<profile>\<run_id>\`
and include:

- `COREX_Node_Editor_installer_bundle_<run_id>.zip`
- `scripts\Install-COREX_Node_Editor.ps1`
- `scripts\Uninstall-COREX_Node_Editor.ps1`
- `installer_manifest.json`
- `installer_validation.json`

The installer script validates install, offscreen startup, and uninstall before
reporting `PASS`.

To hand the app to another Windows user, distribute the generated installer
bundle zip, extract it, and run:

```powershell
.\scripts\Install-COREX_Node_Editor.ps1
```

That installs the packaged folder under
`%LOCALAPPDATA%\COREX_Node_Editor\COREX_Node_Editor\`. The installed app opens
from:

- `%LOCALAPPDATA%\COREX_Node_Editor\COREX_Node_Editor\COREX_Node_Editor.exe`

Remove an installed bundle with:

```powershell
.\scripts\Uninstall-COREX_Node_Editor.ps1
```

## Signing and Verification

Capture a verify-only signing snapshot for the latest installer run in the
selected profile:

```powershell
.\scripts\sign_release_artifacts.ps1 -PackageProfile base -VerifyOnly
```

Sign then verify the latest profile-specific package and installer artifacts:

```powershell
.\scripts\sign_release_artifacts.ps1 -PackageProfile base -CertThumbprint <thumbprint> -TimestampServer <url> -RequireSignedArtifacts
```

The signing script defaults to profile-aware paths:

- Base signing output root: `artifacts\releases\signing\base\`
- Viewer signing output root: `artifacts\releases\signing\viewer\`
- Packaged executable: `artifacts\pyinstaller\dist\<profile>\COREX_Node_Editor\COREX_Node_Editor.exe`
- Installer root: `artifacts\releases\installer\<profile>\`

Environment variable equivalents:

- `EA_SIGN_CERT_THUMBPRINT`
- `EA_SIGN_TIMESTAMP_URL`
- `EA_SIGN_REQUIRE_SIGNED`

Each signing run writes:

- `artifacts\releases\signing\<profile>\<run_id>\signing_manifest.json`
- `artifacts\releases\signing\<profile>\<run_id>\signing_summary.md`

## Release-Doc Guardrails

- `tests/test_packaging_configuration.py` checks that `pyproject.toml`,
  `ea_node_editor.spec`, and the Windows packaging scripts stay aligned.
- `tests/test_markdown_hygiene.py` plus
  `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` catch broken
  canonical-doc links.
- `.\venv\Scripts\python.exe .\scripts\check_traceability.py` is the semantic
  proof gate for packaging, spec-index, pilot, and final QA-matrix drift.

See `docs/specs/perf/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_QA_MATRIX.md` for
the current clean-architecture closeout evidence, and
`docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md` for older archived release
boundaries.
