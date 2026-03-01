# EA Node Editor - Release Candidate Notes

Date: `2026-03-01`

## Shipped Capabilities

- Core editor shell/workspaces/views, graph model, node SDK, execution engine, persistence, and integration nodes (Tracks A-H).
- Full automated QA gate coverage (`unittest` suite) and offscreen performance harness reporting.
- Windows PyInstaller packaging pipeline:
  `ea_node_editor.spec` + `scripts/build_windows_package.ps1`.
- Packaging operator documentation and RC packaging evidence report.

## Known Risks

- Performance baselines in CI/automation are offscreen and may differ from desktop GPU/compositor behavior.
- Packaging smoke test validates startup/liveness only; it is not a full interactive UI acceptance run.
- Unsigned build artifacts are produced (no installer/signing/notarization pipeline in repo).
- Excel XLSX node paths remain runtime dependency-gated when `openpyxl` is not installed.

## Run and Build Commands

- Run tests:
  `venv\Scripts\python -m unittest discover -s tests -v`
- Run benchmark harness:
  `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`
- Run app from source:
  `venv\Scripts\python main.py`
- Build Windows package (+default smoke):
  `.\scripts\build_windows_package.ps1 -Clean`
- Build only (skip smoke):
  `.\scripts\build_windows_package.ps1 -Clean -SkipSmoke`
