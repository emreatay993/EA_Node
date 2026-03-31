# EA Node Editor Spec Pack

This is the canonical requirements/specification set for the Windows-first PyQt6 skeleton core implementation.

`PROGRAM_REQUIREMENTS.txt` remains an upstream source draft. This spec pack is authoritative for implementation.

## Spec Modules

1. [Architecture](requirements/10_ARCHITECTURE.md)
2. [UI/UX](requirements/20_UI_UX.md)
3. [Graph Model](requirements/30_GRAPH_MODEL.md)
4. [Node SDK](requirements/40_NODE_SDK.md)
5. [Node Execution Model](requirements/45_NODE_EXECUTION_MODEL.md)
6. [Execution Engine](requirements/50_EXECUTION_ENGINE.md)
7. [Persistence](requirements/60_PERSISTENCE.md)
8. [Integrations](requirements/70_INTEGRATIONS.md)
9. [Performance](requirements/80_PERFORMANCE.md)
10. [QA + Acceptance](requirements/90_QA_ACCEPTANCE.md)
11. [Traceability Matrix](requirements/TRACEABILITY_MATRIX.md)

Selected work-packet manifests and status ledgers under `docs/specs/work_packets/` are checked in for planning and fresh-thread execution.

## Tracked Work Packet Sets

- [PROJECT_MANAGED_FILES Work Packet Manifest](work_packets/project_managed_files/PROJECT_MANAGED_FILES_MANIFEST.md)
- [PROJECT_MANAGED_FILES Status Ledger](work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md)
- [PROJECT_MANAGED_FILES QA Matrix](perf/PROJECT_MANAGED_FILES_QA_MATRIX.md)
- [ARCHITECTURE_REFACTOR Work Packet Manifest](work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_MANIFEST.md)
- [ARCHITECTURE_REFACTOR Status Ledger](work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md)
- [ARCHITECTURE_REFACTOR QA Matrix](perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md) - historical pointer retained for older docs outside the current packet write scope.
- [ARCHITECTURE_MAINTAINABILITY_REFACTOR Work Packet Manifest](work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_MANIFEST.md)
- [ARCHITECTURE_MAINTAINABILITY_REFACTOR Status Ledger](work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md)
- [ARCHITECTURE_MAINTAINABILITY_REFACTOR QA Matrix](perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md)
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT Work Packet Manifest](work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_MANIFEST.md)
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT Status Ledger](work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md)
- [PYDPF_VIEWER_V1 QA Matrix](perf/PYDPF_VIEWER_V1_QA_MATRIX.md) - closeout evidence only; packet planning docs are archived outside the canonical spec pack.
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT Work Packet Manifest](work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_MANIFEST.md)
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT Status Ledger](work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md)
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT QA Matrix](perf/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md)
- [NODE_EXECUTION_VISUALIZATION Work Packet Manifest](work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_MANIFEST.md)
- [NODE_EXECUTION_VISUALIZATION Status Ledger](work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_STATUS.md)
- [CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK Work Packet Manifest](work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md)
- [CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK Status Ledger](work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md)
- [CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK QA Matrix](perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md)

## ADRs

The legacy ADR markdown files are not retained in this checkout. Use the
requirements modules, retained packet manifests and status ledgers, and the
published QA matrices above as the canonical architecture history on this
branch.
