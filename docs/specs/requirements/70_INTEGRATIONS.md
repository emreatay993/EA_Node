# Integrations Requirements

## Built-In Integration Families
- `REQ-INT-001`: Core built-ins shall remain available without optional third-party integration dependencies.
- `REQ-INT-002`: The repo shall ship built-in integration families for spreadsheet, file I/O, email, process execution, and optional domain-specific integrations through the shared registry/bootstrap path.
- `REQ-INT-003`: Spreadsheet integrations shall cover CSV/XLSX read/write workflows with dependency-gated behavior.
- `REQ-INT-004`: File integrations shall cover text/JSON read/write workflows with path-oriented node contracts.
- `REQ-INT-005`: Email integrations shall cover SMTP/TLS/auth send workflows with explicit configuration.
- `REQ-INT-007`: Built-in integration nodes shall stay grouped under the integrations catalog/bootstrap surface rather than ad-hoc registration paths.
- `REQ-INT-008`: The PyDPF viewer integration surface shall treat `ansys-dpf-core` as the analysis backend and `pyvista`, `pyvistaqt`, plus `vtk` as optional viewer extras; shipped built-ins include `dpf.result_file`, `dpf.model`, `dpf.scoping.mesh`, `dpf.scoping.time`, `dpf.result_field`, `dpf.field_ops`, `dpf.mesh_extract`, `dpf.export`, and `dpf.viewer`; the shipped Ansys DPF catalog taxonomy shall use `category_path` with compute nodes under `("Ansys DPF", "Compute")` and the viewer node under `("Ansys DPF", "Viewer")`; `dpf.viewer` is the first concrete `backend_id` implementation of the generic execution-backend and shell-binder framework (`dpf_embedded`), and repo-local `.rst` / `.rth` fixtures under `tests/ansys_dpf_core/example_outputs/` remain the authoritative smoke inputs for packet-owned verification.

## Acceptance
- `AC-REQ-INT-008-01`: DPF catalog, compute, viewer-backend, binder, packaging, nested-category, and docs/traceability regressions confirm the optional PyDPF viewer stack stays opt-in, the path-backed `Ansys DPF > Compute` and `Ansys DPF > Viewer` taxonomy remains discoverable, its backend-specific binder remains discoverable through the registry wiring, and `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md` plus `docs/specs/perf/NESTED_NODE_CATEGORIES_QA_MATRIX.md` name the retained proof.
