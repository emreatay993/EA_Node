# P04 DPF Materialization Export Backend Wrap-Up

## Implementation Summary
- Packet: P04
- Branch Label: codex/pydpf-viewer-v1/p04-dpf-materialization-export-backend
- Commit Owner: worker
- Commit SHA: e0710505a1cc8b36fd978bb74b43fd73d982e00e
- Changed Files: ea_node_editor/execution/dpf_runtime_service.py, tests/test_dpf_materialization.py, tests/test_dpf_runtime_service.py, docs/specs/work_packets/pydpf_viewer_v1/P04_dpf_materialization_export_backend_WRAPUP.md
- Artifacts Produced: ea_node_editor/execution/dpf_runtime_service.py, tests/test_dpf_materialization.py, tests/test_dpf_runtime_service.py, docs/specs/work_packets/pydpf_viewer_v1/P04_dpf_materialization_export_backend_WRAPUP.md

P04 extends `DpfRuntimeService` with worker-local field extraction, location conversion, norm and min/max helpers, scoped mesh extraction, and explicit viewer materialization or staged export APIs. The materialization contract now exposes `output_profile` values `memory`, `stored`, and `both`.

Durable staged export layouts are explicit and packet-local: `artifacts/dpf/<artifact_key>/field.csv`, `artifacts/dpf/<artifact_key>/preview.png`, `artifacts/dpf/<artifact_key>/vtu/`, and `artifacts/dpf/<artifact_key>/vtm/`. The `vtm` layout uses `dataset.vtm` as the entry file alongside sibling exported `.vtu` blocks.

## Verification
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_dpf_materialization.py tests/test_dpf_runtime_service.py --ignore=venv -q` -> `8 passed in 8.70s`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_dpf_materialization.py --ignore=venv -q` -> `2 passed in 7.77s`
- Final Verification Verdict: PASS

## Manual Test Directives
Too soon for manual testing.

This packet is backend-only and does not expose a user-runnable node, shell action, or viewer session flow yet. Manual checks become worthwhile once `P05`, `P06`, or `P08` wire these helpers into protocol commands or callable graph nodes.

## Residual Risks
- PNG export depends on off-screen `pyvista` and `vtk` rendering remaining available in the target environment; it passed in the project venv used for packet verification.
- `vtu` and `vtm` outputs are staged as directory artifacts so later packets must treat those artifact refs as bundle roots rather than single-file paths.
- Stored exports remain staged artifact refs until the normal project save or promotion flow converts them into managed artifact refs.

## Ready for Integration
- Yes: later packets can reuse `extract_result_fields()`, `convert_fields_location()`, `compute_field_norm()`, `reduce_fields_min_max()`, `extract_mesh()`, `export_field_artifacts()`, and `materialize_viewer_dataset()` without redefining output-profile or artifact-layout semantics.
