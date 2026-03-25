# P14 Ansys Viewer Packaging Wrap-Up

## Implementation Summary
- Packet: `P14`
- Branch Label: `codex/pydpf-viewer-v1/p14-ansys-viewer-packaging`
- Commit Owner: `worker`
- Commit SHA: `d33ee444b49228cd16f6b57d977ad69f577845c5`
- Changed Files: `docs/specs/work_packets/pydpf_viewer_v1/P14_ansys_viewer_packaging_WRAPUP.md, ea_node_editor.spec, pyproject.toml, scripts/build_windows_installer.ps1, scripts/build_windows_package.ps1, tests/test_packaging_configuration.py`
- Artifacts Produced: `docs/specs/work_packets/pydpf_viewer_v1/P14_ansys_viewer_packaging_WRAPUP.md, ea_node_editor.spec, pyproject.toml, scripts/build_windows_installer.ps1, scripts/build_windows_package.ps1, tests/test_packaging_configuration.py`

This packet added opt-in `ansys` and `viewer` dependency groups in `pyproject.toml`, then folded those packages into the aggregate `all` and `dev` extras so the project venv and Windows packaging workflows can opt into full PyDPF coverage without changing the base dependency path.

The Windows packaging path now uses an explicit `base|viewer` package profile. `ea_node_editor.spec` reads `EA_NODE_EDITOR_PACKAGE_PROFILE` and keeps the base build lean by default, while the `viewer` profile explicitly adds DPF gate DLLs, VTK sibling DLLs, PyVistaQt runtime data, and distribution metadata required for `ansys-dpf-core` and the viewer stack inside packaged builds. The PowerShell build and installer scripts now default their output roots by profile, validate the viewer stack before a viewer-enabled build, and record the selected profile in generated packaging metadata.

Packet-owned tests were added to lock the dependency-group wiring, the spec-level runtime hook constants, and the Windows script profile switches into the repo configuration surface owned by this packet.

## Verification
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_packaging_configuration.py --ignore=venv -q` (`3 passed in 0.09s`)
- PASS: `powershell.exe -NoProfile -Command "& { ...Parser]::ParseFile(...) ... }"` (`POWERSHELL_PARSE_OK`)
- Final Verification Verdict: PASS

## Review Gate
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_packaging_configuration.py --ignore=venv -q` (`3 passed in 0.09s`)
- Final Review Gate Verdict: PASS

## Manual Test Directives
- Ready for manual packaging validation.
- Test 1: run `.\scripts\build_windows_package.ps1 -PackageProfile base -Clean -SkipSmoke`; expected result is a base package under `artifacts\pyinstaller\dist\base\COREX_Node_Editor\` without requiring the optional viewer stack.
- Test 2: ensure the venv includes `.[ansys,viewer]` or `.[dev]`, then run `.\scripts\build_windows_package.ps1 -PackageProfile viewer -Clean -SkipSmoke`; expected result is a viewer-enabled package under `artifacts\pyinstaller\dist\viewer\COREX_Node_Editor\` with DPF gate DLLs, `vtk.libs`, and PyVistaQt runtime data bundled by the spec.
- Test 3: run `.\scripts\build_windows_installer.ps1 -PackageProfile viewer` against the viewer dist output; expected result is an installer artifact root under `artifacts\releases\installer\viewer\<run_id>\` whose manifest and validation JSON include `package_profile: viewer`.
- Test 4: run `.\scripts\build_windows_package.ps1 -PackageProfile viewer` from a venv missing the viewer extras; expected result is an early build failure that names the missing `ansys-dpf-core` or viewer packages before PyInstaller starts.

## Residual Risks
- The packet verified configuration coverage and PowerShell parsing, but it did not execute a full `viewer` PyInstaller build in this worktree, so end-to-end runtime confirmation of the bundled DPF and VTK payloads remains a manual packaging check.
- The viewer profile intentionally collects a broad `vtkmodules` hidden-import set for Windows reliability; packaged size may be higher than a later audited minimal VTK subset.

## Ready for Integration
- Yes: the opt-in `ansys` and `viewer` dependency groups are wired into the aggregate extras, the Windows packaging path now separates `base` and `viewer` profiles with explicit viewer runtime asset hooks, the packet-owned tests passed, and the packet is ready for integration on top of `main`.
