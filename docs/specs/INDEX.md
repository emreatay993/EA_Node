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
- [ARCHITECTURE_FOLLOWUP_REFACTOR Work Packet Manifest](work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_MANIFEST.md)
- [ARCHITECTURE_FOLLOWUP_REFACTOR Status Ledger](work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md)
- [ARCHITECTURE_FOLLOWUP_REFACTOR QA Matrix](perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md)
- [ARCHITECTURE_RESIDUAL_REFACTOR Work Packet Manifest](work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_MANIFEST.md)
- [ARCHITECTURE_RESIDUAL_REFACTOR Status Ledger](work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md)
- [ARCHITECTURE_RESIDUAL_REFACTOR QA Matrix](perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md)
- [UI_CONTEXT_SCALABILITY_REFACTOR Work Packet Manifest](work_packets/ui_context_scalability_refactor/UI_CONTEXT_SCALABILITY_REFACTOR_MANIFEST.md)
- [UI_CONTEXT_SCALABILITY_REFACTOR Status Ledger](work_packets/ui_context_scalability_refactor/UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md)
- [UI_CONTEXT_SCALABILITY_REFACTOR QA Matrix](perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md)
- [UI_CONTEXT_SCALABILITY_FOLLOWUP Work Packet Manifest](work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md)
- [UI_CONTEXT_SCALABILITY_FOLLOWUP Status Ledger](work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md)
- [UI_CONTEXT_SCALABILITY_FOLLOWUP QA Matrix](perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md)
- [SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR Work Packet Manifest](work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_MANIFEST.md)
- [SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR Status Ledger](work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md)
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT Work Packet Manifest](work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_MANIFEST.md)
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT Status Ledger](work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md)
- [PYDPF_VIEWER_V1 QA Matrix](perf/PYDPF_VIEWER_V1_QA_MATRIX.md) - closeout evidence only; packet planning docs are archived outside the canonical spec pack.
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT Work Packet Manifest](work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_MANIFEST.md)
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT Status Ledger](work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md)
- [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT QA Matrix](perf/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md)
- [GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK Work Packet Manifest](work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md)
- [GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK Status Ledger](work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md)
- [SHARED_GRAPH_TYPOGRAPHY_CONTROL QA Matrix](perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md)
- [NODE_EXECUTION_VISUALIZATION Work Packet Manifest](work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_MANIFEST.md)
- [NODE_EXECUTION_VISUALIZATION Status Ledger](work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_STATUS.md)
- [NESTED_NODE_CATEGORIES Work Packet Manifest](work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_MANIFEST.md)
- [NESTED_NODE_CATEGORIES Status Ledger](work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_STATUS.md)
- [NESTED_NODE_CATEGORIES QA Matrix](perf/NESTED_NODE_CATEGORIES_QA_MATRIX.md)
- [EXECUTION_EDGE_PROGRESS_VISUALIZATION Work Packet Manifest](work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_MANIFEST.md)
- [EXECUTION_EDGE_PROGRESS_VISUALIZATION Status Ledger](work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md)
- [PERSISTENT_NODE_ELAPSED_TIMES Work Packet Manifest](work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md)
- [PERSISTENT_NODE_ELAPSED_TIMES Status Ledger](work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md)
- [SHARED_GRAPH_TYPOGRAPHY_CONTROL Work Packet Manifest](work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md)
- [SHARED_GRAPH_TYPOGRAPHY_CONTROL Status Ledger](work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md)
- [TITLE_ICONS_FOR_NON_PASSIVE_NODES Work Packet Manifest](work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md)
- [TITLE_ICONS_FOR_NON_PASSIVE_NODES Status Ledger](work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md)
- [PORT_VALUE_LOCKING Work Packet Manifest](work_packets/port_value_locking/PORT_VALUE_LOCKING_MANIFEST.md)
- [PORT_VALUE_LOCKING Status Ledger](work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md)
- [PORT_VALUE_LOCKING QA Matrix](perf/PORT_VALUE_LOCKING_QA_MATRIX.md)
- [DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR Work Packet Manifest](work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_MANIFEST.md)
- [DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR Status Ledger](work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md)
- [CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK Work Packet Manifest](work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md)
- [CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK Status Ledger](work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md)
- [CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK QA Matrix](perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md)
- [NESTED_NODE_CATEGORIES Work Packet Manifest](work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_MANIFEST.md)
- [NESTED_NODE_CATEGORIES Status Ledger](work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_STATUS.md)

## ADRs

The legacy ADR markdown files are not retained in this checkout. Use the
requirements modules, retained packet manifests and status ledgers, and the
published QA matrices above as the canonical architecture history on this
branch.
