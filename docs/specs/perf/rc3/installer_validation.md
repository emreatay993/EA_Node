# RC3 Installer Validation

- Packet: `RC3-P05`
- Date: `2026-03-01`
- Branch label: `rc3/p05-installer-pipeline`

## Verification Commands

1. `powershell -NoProfile -File scripts/build_windows_package.ps1 -SkipSmoke`
2. `powershell -NoProfile -File scripts/build_windows_installer.ps1`

## Packaging Command Result

- Status: **PASS**
- PyInstaller output executable: `artifacts/pyinstaller/dist/EA_Node_Editor/EA_Node_Editor.exe`
- Dependency matrix emitted: `docs/specs/perf/rc3/dependency_matrix.csv`

## Installer Command Result

- Status: **PASS**
- Run id: `20260301_232051`
- Bundle root: `artifacts/releases/installer/20260301_232051/`
- Bundle archive: `artifacts/releases/installer/20260301_232051/EA_Node_Editor_installer_bundle_20260301_232051.zip`
- Manifest: `artifacts/releases/installer/20260301_232051/installer_manifest.json`
- Validation JSON: `artifacts/releases/installer/20260301_232051/installer_validation.json`

## Lifecycle Validation Evidence

- Install phase: `PASS`
- Smoke phase: `PASS` (`5s`, offscreen)
- Uninstall phase: `PASS`
- Post-uninstall executable removal: verified

## Checksums

- Source executable SHA-256: `28818C5CB9161AAFC2D62C824FCF2B2996F54623603C0DFEF967487E01E36277`
- Installer bundle SHA-256: `52CDEDBDCB2E2D003794E90D127C71E472FD5BB0FCB3C3A809DF578703FDB22B`

## Notes

- Installer pipeline is unattended/non-interactive and preserves existing OneDir package as fallback.
- This packet does not include signing; signature integration remains tracked by `RC3-P06`.
