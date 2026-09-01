# COREX Novice Function Plugin SDK QA Matrix

- Updated: `2026-08-29`
- Plan: `docs/PLAN_COREX_NOVICE_PLUGIN_SDK.md`
- Current verdict: `PASS / T17 COMPLETE`
- Release status: pre-release; full verification, clean Windows packaging, and independent final review passed.

## Locked Scope

This matrix retains the evidence for the clean break from public class/descriptor plugins to the dependency-free function SDK. Public source is parsed statically, copied into immutable content-addressed generations, and imported only by an attested process worker. Deterministic schema-2 packages and the guarded registry-replacement transaction are in scope. Compatibility aliases, schema-1 public packages, dependency installation, file watchers, per-plugin interpreters, and a plugin-selectable external runner are not.

Ansys DPF remains an unchanged private trusted family. Custom Workflows remain copied graph snapshots, and Python Script keeps its existing persisted source property. No public plugin source path, bytes, digest, package manifest, bundle/generation record, or callable identity enters project persistence.

## Frozen Inventory And Current Boundary

| Claim | Exact value | Proof owner |
| --- | ---: | --- |
| Public API | 17 public `corex` exports | `corex.__all__`, `tests/test_architecture_boundaries.py` |
| Migration inventory | 936 classified type IDs | `docs/specs/requirements/COREX_NOVICE_PLUGIN_SDK_MIGRATION_INVENTORY.md`, `tests/test_corex_contract_catalog.py` |
| Function conversion | 78 converted type IDs | 68 reserved built-in function entries plus 7 Tabular and 3 MARS entries |
| Private non-DPF boundary | 53 trusted internal exceptions | migration inventory and `tests/test_remaining_builtin_function_migration.py` |
| DPF boundary | 805 DPF exclusions | migration inventory and `tests/test_remaining_builtin_function_migration.py` |
| Non-DPF baseline | 133 frozen non-DPF catalog rows | `tests/fixtures/node_catalog/pre_cutover_non_dpf_catalog.json`, SHA-256 `3CF91390E9E4C606B571ED3C907D7BF35647165F5358328F8FE9C18BF15C618F` |
| Current non-DPF catalog | 131 effective rows | frozen fixture plus documentation, `tests/fixtures/node_catalog/unified_media_panel_structural_overlay.json`, then `tests/fixtures/node_catalog/current_non_dpf_contract_overlay.json` before reuse classification |
| Current Model Viewer default | `surface_with_edges` | strict sole `model.viewer.representation` patch; frozen default remains `surface`; `tests/test_corex_contract_catalog.py` proves frozen/effective/live values and rejects drift, duplicates, unknown keys, extra keys, and out-of-enum replacements |

The task evidence below is historical and intentionally retains the counts observed at each accepted commit; the table above is the current clean-break boundary. Earlier full-verification and package results are not relabeled as current-contract-overlay evidence.

The exact public export order is `node`, `input`, `output`, `text`, `text_area`, `number`, `switch`, `dropdown`, `slider`, `color`, `path`, `interval`, `list`, `Any`, `Image`, `Color`, `Interval`.

## T01-T16 Accepted Commits

| Task | Commit | Retained focused evidence from the live ledger |
| --- | --- | --- |
| T01 | `bc58d7c7` | 938-ID inventory, 133-node golden fixture, catalog/traceability/link/map checks. |
| T02 | `e295676a` | 71 tests and 68 subtests; static declaration SDK, packaging, Ruff, compile, maps, indexes. |
| T03 | `faf001d1` | 73 tests; private function entries/adapters and independent architecture review. |
| T04 | `d27c52f1` | 103 tests; static non-execution, immutable generation, pruning, security review. |
| T05 | `cc4c91c7` | 145 tests and 170 subtests; bounded protocol, registry agreement, client retirement. |
| T06 | `779152bd` | 277 tests and 279 subtests; digest-pinned worker loading and runtime/security review. |
| T07 | `e84e5377` | 285 tests and 256 subtests; deterministic schema 2, archive limits, rollback, package-security/activation reviews. |
| T08 | `2d8d5dbe` | Lanes of 230/145, 93/30, 125/31, and 64/53 with one optional skip; atomic compatible reload/rollback and two independent reviews. |
| T09 | `1a7016d3` | 135 tests; native authoring, no-clobber/attested save, diagnostics, guarded reload, backend/UI reviews. |
| T10 | `e42c0244` | 350 tests and 104 subtests; exact 23-ID built-in conversion and unchanged 133-node fixture. |
| T11 | `fb01e4b3` | 215 tests and 104 subtests; Signal Plot parity, warnings, renderer, DPF exclusion, parser review. |
| T12 | `c9c1e700` | Lanes of 135/23, 64, 212/104, and 24/2 with one optional skip; exact 14 integrations and independent security/behavior review. |
| T13 | `64b8c836` | Eight focused lanes; exact seven Tabular functions, generation attestation, disable gating, review. |
| T14 | `18dd0fe8` | Five focused lanes; exact three MARS functions, provenance/runtime/rollback review. |
| T15 | `f4ab5824` | Seven focused lanes; exact 30-ID final built-in conversion and frozen 68/55/805 boundary. |
| T16 | `eb7a1097` | 300 tests and 138 subtests; exact 17/68/55/805 boundary, zero public legacy SDK, source worker result 37, isolated wheel import, architecture/security review. |

These task results are retained implementation evidence. They are not relabeled as T17 full-verification or Windows-package acceptance.

## Public Documentation And Examples

| Artifact | Current role |
| --- | --- |
| `docs/PLUGIN_AUTHORING_GUIDE.md` | Novice loose-file tutorial, exact decorators/signature/settings/outputs/warnings, schema-2 package and reload workflow. |
| `docs/PLUGIN_MIGRATION_GUIDE.md` | Clean-break migration from class/descriptor plugins and explicit unsupported schema-1 message. |
| `docs/PYTHON_SCRIPT_GUIDE.md` | Distinguishes the persisted workflow-local Python Script node from reusable plugins. |
| `docs/examples/signal_plot_function_plugin.py` | Public function-only Signal Plot example. |
| `docs/examples/strain_conditioner_plugin.py` | Public function-only Strain Conditioner example; spawned process-worker proof returns `37.0`. |
| `tests/fixtures/node_controls/signal_plot_style_node_controls.py` | Private trusted visual fixture only; it is not public authoring guidance. |

Both public examples are statically discovered by `tests/test_novice_plugin_sdk_docs.py`; its real process-worker proof packages and executes the Strain Conditioner example.

## Shipped Contract Evidence

| Area | Retained evidence |
| --- | --- |
| Static discovery | `tests/test_plugin_declaration.py`, `tests/test_plugin_loader.py`, and hostile marker tests prove validation, reload validation, import, and export do not execute public source. |
| Schema and security | `tests/test_package_manager.py` covers exact schema 2, hashes, traversal, links, encryption, duplicates, Windows names, member/size limits, undeclared files, deterministic export, and schema-1 rejection. |
| Immutable execution | `tests/test_plugin_generation.py`, `tests/test_registry_agreement.py`, `tests/test_protocol_codec.py`, `tests/test_client_common.py`, `tests/test_process_client.py`, `tests/test_external_python_client.py`, `tests/test_trusted_client.py`, `tests/test_backend_client.py`, and `tests/test_execution_worker.py` cover approved roots, full registry agreement, digest recheck, lazy import, source mutation, and worker retirement. |
| Reload transaction | `tests/test_registry_replacement.py` covers all-workspace compatibility, active run/viewer refusal, ordered consumer replacement, and exact filesystem/registry/service rollback. |
| Authoring | `tests/test_plugin_authoring.py`, `tests/test_plugin_authoring_dialog.py`, and `tests/test_plugin_authoring_controller.py` cover stable IDs, no-clobber/attested saves, native editor actions, diagnostics, and guarded reload. |
| Persistence | Serializer, fragment, Custom Workflow, Python Script, registry-replacement, and built-in infrastructure tests retain IDs/keys while excluding source/generation records. |
| Legacy removal | `tests/test_architecture_boundaries.py` and `tests/test_dead_code_hygiene.py` pin the 17-name public surface and the absence of public class/descriptor barrels, entry-point/class probing, executable manifests, and schema-1 compatibility. |

## Generated Artifacts

| Artifact | Generator | Current result | Evidence |
| --- | --- | --- | --- |
| `ea_node_editor/addons/ansys_dpf/operator_catalog.json` | `scripts/generate_ansys_dpf_operator_catalog.py` | `PASS` | Generated with ansys-dpf-core 0.16.1: 767 IDs retain exact count/order/version; all 1,051 property records add only the nine default fields below. |
| `docs/qml_navigation_index.{md,json}` | `scripts/generate_qml_navigation_index.py` | `PASS` | Regenerated for 169 QML files; `--check` passed. |
| `docs/architecture_diagrams/{component_map,runtime_pipeline,run_sequence}.{mmd,svg,png}` | `scripts/export_architecture_diagrams.py` with local Mermaid fallback | `PASS / LOCAL RENDER FALLBACK` | All three `.mmd` files exactly match the final Mermaid blocks. Four normal exporter runs and a control POST of the committed old diagram returned Kroki HTTP 500. Mermaid CLI 11.16.0 then rendered all SVG/PNG pairs locally with transparent backgrounds; the PNGs opened successfully in visual review. |
| `docs/source_test_file_index.md` | `scripts/generate_source_test_file_index.py` | `PASS` | Regenerated for 1,134 files; `--check` passed. |
| `docs/agent_route_index.{md,json}` | `scripts/generate_agent_route_index.py` | `PASS` | Regenerated last with 237 route entries; `--check` passed. |

The nine catalog additions are `enum_codes=[]`, `persistence_data_type_id=""`, `nullable=false`, `list_item_type=""`, `list_item_enum_values=[]`, `list_item_enum_codes=[]`, `list_item_minimum=null`, `list_item_maximum=null`, and `list_item_step=0.0`. No descriptor ID, order, DPF version, or other serialized value changed.

## Focused Closeout Results

| Command | Result | Evidence |
| --- | --- | --- |
| `.\venv\Scripts\python.exe -m pytest tests/test_novice_plugin_sdk_docs.py tests/test_non_dpf_node_documentation.py tests/test_corex_contract_catalog.py tests/test_node_title_icon_assets.py tests/test_builtin_function_migration.py tests/test_remaining_builtin_function_migration.py tests/test_architecture_boundaries.py tests/test_dead_code_hygiene.py --ignore=venv -q` | `PASS` | 60 tests and 187 subtests passed. |
| `.\venv\Scripts\python.exe -m pytest tests/test_dpf_operator_catalog_asset.py tests/test_dpf_node_catalog.py tests/test_dpf_generated_operator_catalog.py tests/test_dpf_compute_nodes.py --ignore=venv -q` | `PASS` | 52 tests and 30 subtests passed using the restored ignored fixtures; 12 existing gasket-operator deprecation warnings were emitted. |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_agent_route_index.py tests/test_source_test_file_index.py tests/test_qml_navigation_index.py --ignore=venv -q` | `PASS` | 126 tests and 252 subtests passed. |
| `.\venv\Scripts\python.exe .\scripts\check_traceability.py` | `PASS` | Semantic requirements/traceability audit passed. |
| `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | `PASS` | Repository Markdown-link audit passed. |
| `.\venv\Scripts\python.exe .\scripts\check_agent_maps.py` | `PASS` | Map and route-index path audit passed. |
| Generator `--check` commands for DPF, QML, source/test, and route indexes | `PASS` | All four check-capable generators reported current outputs. The architecture row above records the external Kroki failure and successful local fallback separately. |

## Pending Acceptance Gates

| Gate | Command / Review | Result | Evidence |
| --- | --- | --- | --- |
| Full summarized verification | `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --summarize-output` | `PASS` | `artifacts/verification_logs/20260826_123114/`: fast 3,872 passed/2 skipped; fast serial 220 passed; QML Quick 70 passed; GUI 659 passed/1 skipped; GUI serial 18 passed/1 skipped; slow 46 passed; shell isolation 58 passed. |
| Clean base Windows package | `.\scripts\build_windows_package.ps1 -PackageProfile base -Clean` | `PASS` | Clean base executable SHA-256 `9A9AB243153E10396C326193D2A4C5DAD6DFF551639D9982E9810EFE2652387F`; packaged startup passed, `import corex` and the process-worker function smoke returned `37`, and native Signal Plot produced a PNG. |
| Independent final diff/evidence review | Independent read-only T17 review after final generated outputs and acceptance commands | `PASS` | Final re-review found no remaining issues and returned `CLEAR TO COMPLETE T17`; earlier findings were corrected and reconciled before closeout. |

All three acceptance rows have observed evidence, and the canonical plan ledger records T17 complete. The external Kroki failure stays visible alongside the successful local diagram-render fallback.

## Residual Boundaries

- The bundled COREX runtime is the only plugin execution environment. A plugin-selectable external runner, per-plugin interpreter, dependency installer, watcher, marketplace, and generated typing surface remain unimplemented.
- The existing workflow-level external Python setting remains separate and unchanged.
- Restored files under `tests/ansys_dpf_core/example_outputs/` are ignored test inputs and must not be staged.
- Four historical performance reports required by the slow lane were restored byte-for-byte from commit `c30c1f65`; they remain ignored prerequisites and must not be staged.
- Commit and publication remain separate repository operations after acceptance closeout.
