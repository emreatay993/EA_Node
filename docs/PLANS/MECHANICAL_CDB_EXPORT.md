# Mechanical CDB Export

## Approved outcome

Extend Save Mechanical Model with blocked CDB export for Static Structural in
Mechanical 2026 R1. Keep the existing node and its Model, Files, and Report
outputs. Support standalone and selected Workbench models.

- Add `cdb` to Format and file filters, including automatic extension detection.
- Add a CDB options group: Content, Analysis, and Load step. Default Content to
  mesh and named selections, and Load step to 1. Resolve an empty Analysis only
  when one eligible analysis exists. Ignore Load step in mesh mode.
- Mesh mode exports the existing undeformed physical mesh, solver-exported
  named-selection components, and necessary element definitions. Exclude
  material properties, loads, supports, and generated contact elements.
- Full mode exports the supported native finite-element database and one
  selected load-step definition. It does not export solved state or history.
- Require an existing current mesh. Do not remesh or solve automatically. Reject
  unsupported analysis dependencies and solve-bearing command snippets.
- Prepare native output in disposable same-release owners from a staged native
  snapshot. Validate native readback before rollback-protected publication.
- Preserve source files, existing results, user commands, and admissible model
  ownership. Retain existing project-save and archive behavior.

## Execution

| Task | Owner | Status | Acceptance / next action |
| --- | --- | --- | --- |
| T01 Native helper and qualification | Coordinator; independent reviewer `01a09b14-89ec-7071-b6f3-4d0877b7fbed` | Accepted | Native mesh/full, selected steps, Unicode, and contact cases pass. Final helper suite has 64 tests; required native-path refinements were independently reviewed. |
| T02 Save integration | Worker `01a09b2e-27bd-7203-88ef-53fe2f3b7243`; reviewer `01a09b53-0257-74d3-a703-95ca16f08025` | Accepted | 65 CDB integration tests pass. Source-preservation/protocol and native filename-extension fixes reviewed; registered standalone and Workbench workflows pass. |
| T03 Regression and documentation | Documentation worker `01a09b4d-3b6a-7eb0-b472-6b04fc90ff0c`; final reviewer `01a09b76-bf00-7c51-8d1e-2866dd18f3ca` | Accepted | 592 final tests pass. Guide, examples, catalog fixture, and maps agree; native source-family and overwrite checks pass; final review has no blockers. |

The coordinator owns this table. One implementation writer is active at a time.
Each substantial task receives independent review before acceptance. The user
subsequently requested committing the completed changes and pushing to `main`.

## Acceptance

- Native mesh round-trip preserves physical mesh IDs, connectivity, and eligible
  named-selection membership while omitting excluded physics.
- Native full-mode round-trip preserves supported material, section, contact,
  and load data, with a demonstrated difference between two selected steps.
- Exercise standalone and Workbench sources, analysis ambiguity, invalid steps,
  missing/stale mesh, and unsupported execution dependencies.
- Exercise Unicode paths, overwrite refusal, cancellation, native failure,
  publication rollback, and model output/receipt validation.
- Keep existing save/archive tests passing, update exact control inventories,
  regenerate affected Mechanical examples, and run relevant documentation and
  agent-map checks. Mocks alone do not satisfy native acceptance.

## Baseline

Implementation starts at `204a8bb20e70a41d6fe655c318222f28ebd815fb` in the main
project checkout. Preserve these unrelated pre-existing changes:

- `docs/specs/INDEX.md`
- `tests/fixtures/graph_canvas_surface_snapshot.json`
- `docs/PLAN_COREX_Physical_Simulation_Backend.md`
- `scripts/Strain_Gage_Positioning/modular_version/strain_candidate_points.csv`

## Defaults and exclusions

Export the whole selected analysis. CDB import, deformed mesh, result export,
batch load-step export, and other analysis families are outside this change.

## Final evidence

The final owning-route verification passed **592 tests in 42.76 seconds**:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue tests/test_corex_contract_catalog.py tests/test_repo_owned_node_documentation.py -q -n 0
```

Targeted Ruff, traceability, Markdown-link, agent-map, and diff whitespace checks
pass. Examples and the route index were regenerated through their existing
owners. The catalogue retains 147 node IDs; only Save Mechanical Model changes.
Its three new controls bring the Mechanical catalogue to 55 inputs, 22 outputs,
and 77 ports, and the repository's resolved catalogue to 619 ports.

| Native case | Accepted evidence |
| --- | --- |
| Full step 1 and step 3 | Independent readback retains 541 nodes and 108 elements; equal mesh digests and different load-state digests. |
| Mesh with Unicode destination | Independent readback retains 541 nodes, 96 physical elements, and the solver-exported named selection. |
| Contact-bearing model | Full readback retains 156 elements; mesh readback retains the 96 physical elements and necessary definitions. |
| Registered standalone Mesh | Open, Save CDB, and continued use of the source Model complete; revisions 0/1/2; original source preserved; 23 tracked processes and zero survivors. |
| Registered Workbench Full step 3, Unicode destination | Same registered chain completes with revisions 0/1/2; original project bundle preserved; 48 tracked processes and zero survivors after bounded settling. |
| Registered overwrite refusal | Existing CDB bytes and source remain unchanged; expected Save failure; zero process survivors. |

Detailed receipts and the final test log remain under the ignored
`artifacts/mechanical_cdb_qualification/` root. The saved Workbench UTF-8 evidence
and final published CDB receipt were validated after correcting a console-only
encoding error that occurred after all native assertions had passed.

Independent reviews accepted native export, source/save integration, the
source-working-copy error-path fix, preservation of Mechanical filename
extensions through Windows short-directory aliases, and final documentation/
catalogue consistency. No numerical solve or implicit remesh is performed by
export. Live Ansys GUI qualification is not claimed. Unicode native working paths
require usable, identity-checked Windows short names. The unrelated baseline
changes remain preserved and excluded from the CDB commit.
