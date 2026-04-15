# ANSYS DPF Full Plugin Rollout QA Matrix

- Updated: `2026-04-15`
- Packet set: retained `ANSYS_DPF_FULL_PLUGIN_ROLLOUT` (`P00` through `P07`)
- Scope: final closeout matrix for the optional, version-aware DPF plugin lifecycle, workflow-first taxonomy, generated operator and helper rollout, source-aware runtime materialization, missing-plugin placeholder portability, and retained docs/traceability evidence.

## Locked Scope

- `ansys-dpf-core` remains optional. Startup without DPF must keep the rest of the app usable.
- Built-in DPF registration is descriptor-first and version-aware. Startup records the installed `ansys-dpf-core` version, refreshes the shipped descriptor cache when that version changes, and keeps provenance-aware descriptor loading ahead of legacy constructor probing.
- The shipped DPF surface is workflow-first: `Ansys DPF > Inputs`, `Ansys DPF > Workflow`, `Ansys DPF > Helpers > ...`, `Ansys DPF > Operators > <Family>`, and `Ansys DPF > Viewer` are the visible root families for the retained rollout.
- Generated operator wrappers and curated helper workflow families now ship as first-class descriptors, but the broad `Ansys DPF > Advanced > Raw API Mirror` / non-operator `ansys.dpf.core` reflection surface remains deferred.
- Runtime materialization must bind helper-originated model, scoping, mesh, fields-container, and generic object handles for generated operators without regressing the existing handwritten `dpf.field_ops` `ElementalNodal` passthrough.
- Missing-plugin placeholders preserve saved labels, values, optional-port state, exposure metadata, and unresolved edges, but they stay non-executable and read-only until the DPF plugin is available again.
- Repo-local `.rst` and `.rth` fixtures under `tests/ansys_dpf_core/example_outputs/` remain the authoritative smoke inputs for packet-owned verification.
- The rollout closeout keeps the earlier backend-preparation review and QA matrix as retained proof; this packet set does not reopen unrelated repo-wide verification beyond the declared packet commands and closeout gates.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| Planner bootstrap, packet manifest publication, and status-ledger gate | `P00` | `REQ-QA-038` | `planner file gate: ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P00_FILE_GATE_PASS`; `planner status gate: ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P00_STATUS_PASS` | PASS in `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P00_bootstrap_WRAPUP.md` (`010eefa96c0d2d98bbdccb63d744e77c82280a96`) |
| Version-aware plugin lifecycle, builtin descriptor cache refresh, and optional DPF startup gating | `P01` | `REQ-INT-009`, `REQ-QA-038` | `.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py tests/test_dpf_node_catalog.py --ignore=venv -q` | PASS in `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P01_versioned_plugin_lifecycle_WRAPUP.md` (`46aa710bbeff264b85757e507b320dcbc793d137`) |
| Descriptor-contract expansion for source metadata, generated ports, and registry/runtime validation | `P02` | `REQ-INT-009`, `REQ-QA-038` | `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py tests/test_dpf_contracts.py --ignore=venv -q` | PASS in `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P02_contract_expansion_WRAPUP.md` (`b1ae8520a6f207b6cedbb95d1f63832851817c45`) |
| Workflow-first DPF family taxonomy, catalog ordering, and library-filter coverage | `P03` | `REQ-INT-008`, `REQ-QA-038` | `.\venv\Scripts\python.exe -m pytest tests/test_dpf_library_taxonomy.py tests/test_dpf_node_catalog.py tests/test_registry_filters.py --ignore=venv -q` | PASS in `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P03_family_taxonomy_WRAPUP.md` (`0dce2c51fb7de3067db53b90043a87a42af806a5`) |
| Generated operator-family discovery, descriptor publication, and foundational operator preservation | `P04` | `REQ-INT-008`, `REQ-INT-009`, `REQ-QA-038` | `.\venv\Scripts\python.exe -m pytest tests/test_dpf_generated_operator_catalog.py tests/test_dpf_node_catalog.py --ignore=venv -q` | PASS in `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P04_operator_families_WRAPUP.md` (`d6a87ec6a6ab6b511f632a456d62839978d33c0a`) |
| Curated helper workflow families, callable-backed metadata, and fixture-backed helper execution coverage | `P05` | `REQ-INT-008`, `REQ-INT-009`, `REQ-QA-038` | `.\venv\Scripts\python.exe -m pytest tests/test_dpf_generated_helper_catalog.py tests/test_dpf_workflow_helpers.py --ignore=venv -q` | PASS in `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P05_helper_workflow_families_WRAPUP.md` (`55add96618d510689d9cc0371bc861a8cd8804a2`) |
| Generated-operator runtime materialization, helper object-handle portability, and placeholder reopen coverage | `P06` | `REQ-INT-009`, `REQ-QA-038` | `.\venv\Scripts\python.exe -m pytest tests/test_dpf_materialization.py tests/test_dpf_runtime_service.py tests/test_serializer.py tests/test_serializer_schema_migration.py --ignore=venv -q` | PASS in `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P06_runtime_persistence_portability_WRAPUP.md` (`195a271fef4ee408dbfeb670b43d16051e9aae17`) |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py --ignore=venv -q` | Packet-owned traceability and markdown-hygiene regression for the final DPF rollout closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Review-gate proof audit for the retained architecture, README, requirements, QA matrix, and traceability docs |

## 2026-04-15 Execution Results

| Command | Result | Notes |
|---|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py --ignore=venv -q` | PASS | Packet-owned closeout tests confirmed the new QA matrix, workflow-first README and architecture guidance, updated integration and QA requirements, and the retained traceability rows for the shipped Ansys DPF rollout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the DPF rollout requirements, QA matrix, README, architecture, and traceability refresh landed in the packet worktree |

## Retained Manual Evidence

1. Missing-dependency startup check: start the app without `ansys-dpf-core` and confirm startup succeeds, non-DPF nodes remain available, and the `Ansys DPF` library family does not appear.
2. Installed-dependency catalog check: start the app with DPF installed, confirm the descriptor cache refreshes when the installed backend version changes, and verify the library exposes `Ansys DPF > Inputs`, `Ansys DPF > Workflow`, `Ansys DPF > Helpers`, `Ansys DPF > Operators`, and `Ansys DPF > Viewer`.
3. Generated-operator workflow smoke check: open a workspace that uses helper-backed `DataSources` / `Model` nodes plus a generated operator such as `dpf.op.result.displacement` against a repo-local `.rst` or `.rth` fixture and confirm the run completes without new DPF runtime binding errors.
4. Missing-plugin reopen check: save a project containing foundational and generated `dpf.*` nodes, reopen it without the DPF plugin, and confirm the nodes remain visible as read-only placeholders with saved labels, values, optional-port state, and connectivity.
5. Placeholder rebind check: reopen the same project with DPF available again and confirm the placeholders rebind into live DPF nodes without losing the saved graph structure.

## Residual Risks

- `P07` is docs-and-proof only. It does not rerun a new broad DPF aggregate outside the retained packet verification commands and the declared closeout gates.
- The broad `Ansys DPF > Advanced > Raw API Mirror` / non-operator `ansys.dpf.core` reflection surface remains intentionally deferred to a later packet set.
- Generated operator outputs still surface native DPF objects rather than a fully generic output-handle layer, so downstream interop remains strongest through existing wrapper and helper nodes.
- The inherited `tests/test_dpf_library_taxonomy.py` exact-helper-set anchor from `P03` still predates the `P05` helper expansion and remains outside this packet set's retained verification surface.
- The installed DPF package still emits deprecation warnings for gasket deformation aliases during catalog discovery and runtime materialization; retained packet verification passes through those warnings unchanged.
