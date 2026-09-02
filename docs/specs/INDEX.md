# EA Node Editor Spec Pack

This is the canonical requirements/specification set for the Windows-first PyQt6 skeleton core implementation.

`PROGRAM_REQUIREMENTS.txt` remains an upstream source draft. This spec pack is authoritative for implementation.

Corex is still pre-release. The authoritative modernization direction is Option B: a GUI-independent headless Corex kernel with explicit extension contracts, with the QML shell acting as one client. Current-schema `.cxproj` persistence, canonical action IDs, surface/input contracts, headless execution APIs, and runtime/toolchain/artifact descriptors are planned public interfaces; old `.cxproj`, plugin, QML, action, and import compatibility may be broken when cleanup removes architecture ambiguity.

The locked execution baseline is dependency-driven DataTree flow. Active nodes expose only `data` ports with author-declared Item/List/Tree access; unrelated passive authoring may still use `flow`. Execution, completed, failed, On Failure, and Start/End/Branch routing ports or nodes are retired without compatibility aliases. The coordinated contract is defined across the UI/UX, Node SDK, Node Execution Model, Execution Engine, Persistence, Performance, QA, and Traceability modules below.

## Spec Modules

1. [Architecture](requirements/10_ARCHITECTURE.md)
2. [UI/UX](requirements/20_UI_UX.md)
3. [Graph Model](requirements/30_GRAPH_MODEL.md)
4. [Node SDK](requirements/40_NODE_SDK.md) — public guides: [Novice Plugin Authoring](../PLUGIN_AUTHORING_GUIDE.md), [Legacy Plugin Migration](../PLUGIN_MIGRATION_GUIDE.md), [Python Script Nodes](../PYTHON_SCRIPT_GUIDE.md); executable examples: [Signal Plot](../examples/signal_plot_function_plugin.py), [Strain Conditioner](../examples/strain_conditioner_plugin.py)
5. [Node Execution Model](requirements/45_NODE_EXECUTION_MODEL.md)
6. [Execution Engine](requirements/50_EXECUTION_ENGINE.md)
7. [Persistence](requirements/60_PERSISTENCE.md)
8. [Integrations](requirements/70_INTEGRATIONS.md)
9. [Performance](requirements/80_PERFORMANCE.md)
10. [QA + Acceptance](requirements/90_QA_ACCEPTANCE.md)
11. [Traceability Matrix](requirements/TRACEABILITY_MATRIX.md)

## Capability Roadmap Status

These rows summarize whole-capability status. `PARTIAL` means accepted backend and persistence requirements coexist with planned UX; it is not a release claim. Exact requirement-level implementation and planned-state records live in the [Traceability Matrix](requirements/TRACEABILITY_MATRIX.md).

| Research opportunity | COREX capability | Requirements | Status |
| --- | --- | --- | --- |
| `SYN-OPP-0001` | Linked workflow instances | `REQ-PERSIST-025`, `REQ-UI-051` | `PLANNED` |
| `SYN-OPP-0002` | Durable solution snapshots and incremental recomputation | `REQ-EXEC-017`, `REQ-PERSIST-026`, `REQ-UI-052` | `PARTIAL` |
| `SYN-OPP-0003` | Unified workflow interface semantics | `REQ-NODE-036`, `REQ-UI-053` | `PLANNED` |
| `SYN-OPP-0004` | Dependency and provenance inspector | `REQ-EXEC-018`, `REQ-UI-054` | `PLANNED` |
| `SYN-OPP-0005` | Reproducible debug bundles | `REQ-EXEC-019`, `REQ-UI-055` | `PLANNED` |
| `SYN-OPP-0006` | Secure remote execution | `REQ-EXEC-020`, `REQ-INT-018`, `REQ-UI-056` | `PLANNED` |
| `SYN-OPP-0007` | Solver-neutral FEA process contracts | `REQ-NODE-037`, `REQ-EXEC-021`, `REQ-INT-019`, `REQ-UI-057` | `PLANNED` |
| `SYN-OPP-0008` | Permissioned agent orchestration | `REQ-ARCH-020`, `REQ-EXEC-022`, `REQ-UI-058` | `PLANNED` |

## Active Implementation Plans — No Implementation Proof

- [COREX Runtime, Registry, and Presentation Ownership Refactor](../PLAN_COREX_RUNTIME_REGISTRY_PRESENTATION_REFACTOR.md) — `CHECKPOINT — T14 ACCEPTED; NEXT T15`; [QA ledger](perf/COREX_RUNTIME_REGISTRY_PRESENTATION_REFACTOR_QA_MATRIX.md)

### Completed Semantic-Type Architecture and Evidence

T01–T17 are complete, and the locked 176-type snapshot is fully classified.

### Completed Implementation Plans

- [COREX Maintainability And Ownership Refactor](../PLAN_COREX_MAINTAINABILITY_OWNERSHIP_REFACTOR.md) — `COMPLETED — T00–T08 ACCEPTED`
- [COREX Incremental Execution And Solution Snapshots](../PLAN_COREX_INCREMENTAL_EXECUTION_AND_SOLUTION_SNAPSHOTS.md) — `COMPLETED — T01–T09 ACCEPTED`
- [COREX Novice Function Plugin SDK](../PLAN_COREX_NOVICE_PLUGIN_SDK.md) — `COMPLETED — T01–T17; RETAINED QA EVIDENCE BELOW`
- [COREX Application-Default External Python Runtime](../PLAN_COREX_EXTERNAL_PYTHON_RUNTIME.md) — `COMPLETED — T01–T05 ACCEPTED`
- [COREX Unified Media Panel](../PLAN_COREX_UNIFIED_MEDIA_PANEL.md) — `COMPLETED — T01–T10 ACCEPTED`

Work-packet manifests, status ledgers, and per-phase wrap-up documents formerly stored under `docs/specs/work_packets/` were pruned from the repository (commit `0b426a31`) and are now recorded only in git history. Historical examples include `COREX_EXCALIDRAW_REAL_EDITOR_MANIFEST.md` and `COREX_EXCALIDRAW_REAL_EDITOR_STATUS.md`. The published QA matrices below remain the retained closeout evidence for each tracked packet set; there is no live work-packet document directory in the current tree.

## Retained Work-Packet QA Evidence

- [COREX Maintainability And Ownership Refactor QA Matrix](perf/COREX_MAINTAINABILITY_OWNERSHIP_REFACTOR_QA_MATRIX.md) - retained T00–T08 task, migration, review, correctness, and advisory performance closeout evidence.
- [Verification Speed QA Matrix](perf/VERIFICATION_SPEED_QA_MATRIX.md)
- [COREX Change Locality QA Matrix](perf/COREX_CHANGE_LOCALITY_QA_MATRIX.md)
- [COREX Internal Performance Improvement QA Matrix](perf/COREX_INTERNAL_PERFORMANCE_IMPROVEMENT_QA_MATRIX.md)
- [COREX Novice Function Plugin SDK QA Matrix](perf/COREX_NOVICE_PLUGIN_SDK_QA_MATRIX.md) - retained T17 closeout evidence; full verification, clean Windows packaging, and final independent review passed.
- [PROJECT_MANAGED_FILES QA Matrix](perf/PROJECT_MANAGED_FILES_QA_MATRIX.md)
- [ARCHITECTURE_REFACTOR QA Matrix](perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md) - historical pointer retained for older docs outside the current packet write scope.
- [ARCHITECTURE_MAINTAINABILITY_REFACTOR QA Matrix](perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md)
- [ARCHITECTURE_FOLLOWUP_REFACTOR QA Matrix](perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md)
- [ARCHITECTURE_RESIDUAL_REFACTOR QA Matrix](perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md)
- [UI_CONTEXT_SCALABILITY_REFACTOR QA Matrix](perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md)
- [UI_CONTEXT_SCALABILITY_FOLLOWUP QA Matrix](perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md)
- [PYDPF_VIEWER_V1 QA Matrix](perf/PYDPF_VIEWER_V1_QA_MATRIX.md) - closeout evidence only; packet planning docs are archived outside the canonical spec pack.
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT QA Matrix](perf/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md)
- [COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION QA Matrix](perf/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_QA_MATRIX.md)
- [COREX_NO_LEGACY_ARCHITECTURE_CLEANUP QA Matrix](perf/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md)
- [COREX_CLEAN_ARCHITECTURE_RESTRUCTURE QA Matrix](perf/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_QA_MATRIX.md)
- [COREX_ARCHITECTURE_MODERNIZATION QA Matrix](perf/COREX_ARCHITECTURE_MODERNIZATION_QA_MATRIX.md)
- [Hybrid Direct Tabular Auto-Plotting QA Matrix](perf/HYBRID_DIRECT_TABULAR_AUTO_PLOTTING_QA_MATRIX.md)
- [SHARED_GRAPH_TYPOGRAPHY_CONTROL QA Matrix](perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md)
- [NESTED_NODE_CATEGORIES QA Matrix](perf/NESTED_NODE_CATEGORIES_QA_MATRIX.md)
- [TITLE_ICONS_FOR_NON_PASSIVE_NODES QA Matrix](perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md)
- [TOOLTIP_MANAGER_TIERS QA Matrix](perf/TOOLTIP_MANAGER_TIERS_QA_MATRIX.md)
- [Default Value Grips QA Matrix](perf/DEFAULT_VALUE_GRIPS_QA_MATRIX.md)
- [Node Execution Visualization QA Matrix](perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md)
- [DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR QA Matrix](perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md)
- [ANSYS_DPF_FULL_PLUGIN_ROLLOUT QA Matrix](perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md)
- [ADDON_MANAGER_BACKEND_PREPARATION QA Matrix](perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md)
- [CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK QA Matrix](perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md)
- [MEDIA_VIEWER_CONTENT_FULLSCREEN QA Matrix](perf/MEDIA_VIEWER_CONTENT_FULLSCREEN_QA_MATRIX.md)
- [COREX_EXCALIDRAW_WEB_HOST_LAYER QA Matrix](perf/COREX_EXCALIDRAW_WEB_HOST_LAYER_QA_MATRIX.md)
- [COREX_EXCALIDRAW_REAL_EDITOR QA Evidence](perf/COREX_EXCALIDRAW_WEB_HOST_LAYER_QA_MATRIX.md) - retained in the Excalidraw web-host matrix with the real local/offline editor follow-up proof.
- [CHROMIUM_WEBSITE_HTML_VIEWER_NODE QA Matrix](perf/CHROMIUM_WEBSITE_HTML_VIEWER_NODE_QA_MATRIX.md)
- [V1_CLASSIC_EXPLORER_FOLDER_NODE QA Matrix](perf/V1_CLASSIC_EXPLORER_FOLDER_NODE_QA_MATRIX.md)
- [COREX Graph Mutation Churn Remediation Closeout Evidence](perf/TRACK_H_BENCHMARK_REPORT.md)
- [Graph Canvas Perf QA Matrix](perf/GRAPH_CANVAS_PERF_QA_MATRIX.md)
- [COREX Neutral CAD/FE Model Viewer V1 QA Matrix](perf/ENGINEERING_VIEWER_V1_QA_MATRIX.md) - implementation and release-gate evidence; format-fixture and lazy FE acceptance remain open.
- [COREX Neutral CAD/FE Model Viewer V1 Native Performance Report](perf/ENGINEERING_VIEWER_V1_NATIVE_PERF_REPORT.md) - display-attached Windows/D3D11 acceptance evidence.

## ADRs

Retained ADR markdown files under `adrs/` are historical context only. The
requirements modules, the published QA matrices above, and the packet history
in git are the canonical architecture history on this branch. When an ADR's
original compatibility rationale conflicts with the pre-release modernization
baseline, the current requirements pack wins.
