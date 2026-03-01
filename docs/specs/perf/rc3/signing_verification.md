# RC3 Signing Verification

- Packet: `RC3-P06`
- Date: `2026-03-01`
- Branch label: `rc3/p06-signing-and-verification`

## Verification Commands

1. `powershell -NoProfile -File scripts/sign_release_artifacts.ps1 -VerifyOnly`
2. `powershell -NoProfile -File scripts/build_windows_package.ps1 -SkipSmoke`

## Signing Verification Result

- Status: **PASS**
- Run id: `20260301_232746`
- Manifest: `artifacts/releases/signing/20260301_232746/signing_manifest.json`
- Summary: `artifacts/releases/signing/20260301_232746/signing_summary.md`
- Mode: `verify_only`
- Require signed artifacts: `False`
- Certificate thumbprint source: `EA_SIGN_CERT_THUMBPRINT` (not set in this run)
- Timestamp URL source: `EA_SIGN_TIMESTAMP_URL` (not set in this run)
- Installer run detected: `20260301_232051`

## Target Snapshot (Verify-Only)

| Target | Exists | Signable | Signature Status |
|---|---|---|---|
| `artifacts/pyinstaller/dist/EA_Node_Editor/EA_Node_Editor.exe` | `True` | `True` | `NotSigned` |
| `artifacts/releases/installer/20260301_232051/EA_Node_Editor_installer_bundle_20260301_232051.zip` | `True` | `False` | `UnknownError` |
| `artifacts/releases/installer/20260301_232051/scripts/Install-EA_Node_Editor.ps1` | `True` | `True` | `NotSigned` |
| `artifacts/releases/installer/20260301_232051/scripts/Uninstall-EA_Node_Editor.ps1` | `True` | `True` | `NotSigned` |

## Packaging Rebuild Result

- Status: **PASS**
- Command: `powershell -NoProfile -File scripts/build_windows_package.ps1 -SkipSmoke`
- Rebuilt executable: `artifacts/pyinstaller/dist/EA_Node_Editor/EA_Node_Editor.exe`
- Dependency matrix: `docs/specs/perf/rc3/dependency_matrix.csv`

## Strict Gate Check (Supplementary)

- Command:
  - `$env:EA_SIGN_REQUIRE_SIGNED='1'; powershell -NoProfile -File scripts/sign_release_artifacts.ps1 -VerifyOnly`
- Status: **PASS (expected failure observed)**
- Strict-run manifest: `artifacts/releases/signing/20260301_233011/signing_manifest.json`
- Strict-run summary: `artifacts/releases/signing/20260301_233011/signing_summary.md`
- Observed exit code: `1` due to unsigned signable targets.

## Policy Notes

- Signing secrets remain externalized via environment variables and certificate store lookup.
- Release gates can enforce strict signature validation by setting `EA_SIGN_REQUIRE_SIGNED=1` (or equivalent true value), which causes non-valid signatures on signable targets to fail the command.
