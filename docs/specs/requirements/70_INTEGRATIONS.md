# Integrations Requirements

## Built-In Integration Families
- `REQ-INT-001`: Core built-ins shall remain available without optional third-party integration dependencies.
- `REQ-INT-002`: The repo shall ship built-in integration families for spreadsheet, file I/O, email, process execution, and optional domain-specific integrations through the shared registry/bootstrap path.
- `REQ-INT-003`: Spreadsheet integrations shall cover CSV/XLSX read/write workflows with dependency-gated behavior.
- `REQ-INT-004`: File integrations shall cover text/JSON read/write workflows with path-oriented node contracts.
- `REQ-INT-005`: Email integrations shall cover SMTP/TLS/auth send workflows with explicit configuration.
- `REQ-INT-007`: Built-in integration nodes shall stay grouped under the integrations catalog/bootstrap surface rather than ad-hoc registration paths.
- `REQ-INT-008`: The PyDPF viewer integration surface shall treat `ansys-dpf-core` as the analysis backend and `pyvista`, `pyvistaqt`, plus `vtk` as optional viewer extras; shipped built-ins include `dpf.load_result`, `dpf.result_field`, `dpf.mesh`, `dpf.export`, and `dpf.viewer`, and repo-local `.rst` / `.rth` fixtures under `tests/ansys_dpf_core/example_outputs/` remain the authoritative smoke inputs for packet-owned verification.

## Acceptance
- `AC-REQ-INT-008-01`: DPF catalog, compute, viewer, packaging, and docs/traceability regressions confirm the optional PyDPF viewer stack stays opt-in, its built-in node family remains discoverable, and the published QA matrix names both repo-local fixture smoke inputs and Windows packaged-build follow-up checks.
