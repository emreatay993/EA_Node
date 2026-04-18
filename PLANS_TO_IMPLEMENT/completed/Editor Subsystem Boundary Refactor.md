# Editor Subsystem Boundary Refactor

## Summary
- Reslice the live editor codebase along the seams it already exposes so graph state, persistence, node loading, workspace/runtime contracts, execution assembly, and shell/QML wiring can evolve independently without changing user-facing behavior. The implementation split is intentionally subagent-first: each execution task names one primary source subagent and one primary regression subagent so the work can later convert into packets without rediscovering ownership boundaries.

## Key Changes
- Extract a narrower graph-domain boundary so `GraphModel` stops carrying normalization, mutation-policy, and persistence-adjacent responsibilities at once.
- Separate persistence codec, migration, and unresolved overlay handling so authored document shape and live runtime repair are not normalized in multiple places.
- Split node/plugin discovery, workspace/runtime contracts, execution assembly, and shell/QML wiring into explicit subsystem-owned seams instead of one broad refactor wave.
- Finish with verification, packaging, and architecture-traceability updates so the repo's path-driven enforcement stays synchronized with the new module layout.

## Public Interface Changes
- `none`

## Execution Tasks

### T01 Graph State and Mutation Boundary
- Primary source subagent: `graph-core`
- Primary regression subagent: `verification-control-plane`
- Goal: separate mutable project/workspace state from normalization and mutation-policy logic so `ea_node_editor/graph/model.py` can act as a state boundary instead of a grab bag for repair, rewrite, and persistence-adjacent behavior.
- Preconditions: `none`
- Conservative write scope: `ea_node_editor/graph/model.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/graph/rules.py`, `ea_node_editor/graph/port_locking.py`, `ea_node_editor/graph/transform_*.py`, `tests/test_port_locking.py`, `tests/test_comment_backdrop_membership.py`, `tests/graph_track_b/scene_model_graph_model_suite.py`
- Deliverables: narrower graph-state entrypoints, explicit ownership split between state, normalization, and mutation helpers, updated imports at direct call sites, and focused graph-core regression coverage.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/test_port_locking.py tests/test_comment_backdrop_membership.py tests/graph_track_b/scene_model_graph_model_suite.py --ignore=venv -q`
- Non-goals: no persistence codec split, no node/plugin loader changes, no shell/QML rewiring.
- Packetization notes: likely `P01`; `T03` can run in parallel, but `T02` and later adoption tasks should consume the resulting graph-state contract instead of reopening it.

### T02 Persistence Document and Overlay Boundary
- Primary source subagent: `persistence-stack`
- Primary regression subagent: `verification-control-plane`
- Goal: split authored-document codec work, migration/repair logic, and unresolved overlay storage so persistence stops normalizing workspace/project metadata in multiple places.
- Preconditions: `T01`
- Conservative write scope: `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/persistence/migration.py`, `ea_node_editor/persistence/overlay.py`, `ea_node_editor/persistence/artifact_store.py`, `ea_node_editor/persistence/session_store.py`, `tests/test_serializer.py`, `tests/test_serializer_schema_migration.py`, `tests/test_project_artifact_resolution.py`, `tests/test_project_artifact_store.py`, `tests/fixtures/persistence/*`
- Deliverables: one codec-facing document-shape boundary, one overlay-facing unresolved-state boundary, migration ownership cleanup, and focused persistence regression updates.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_project_artifact_resolution.py tests/test_project_artifact_store.py --ignore=venv -q`
- Non-goals: no execution pipeline refactor yet, no packaging manifest churn, no shell bridge changes.
- Packetization notes: likely `P02`; this task should unblock `T04`, `T05`, and `T06` without widening back into graph mutation work.

### T03 Node Registry and Plugin Loading Boundary
- Primary source subagent: `nodes-system`
- Primary regression subagent: `verification-control-plane`
- Goal: separate plugin discovery/provenance from registry validation/coercion so node-package loading can evolve without widening the registry ownership surface.
- Preconditions: `none`
- Conservative write scope: `ea_node_editor/nodes/registry.py`, `ea_node_editor/nodes/plugin_loader.py`, `ea_node_editor/nodes/node_specs.py`, `ea_node_editor/nodes/plugin_contracts.py`, `ea_node_editor/nodes/builtins/*`, `tests/test_plugin_loader.py`, `tests/test_registry_validation.py`, `tests/test_registry_filters.py`, `tests/test_node_package_io_ops.py`
- Deliverables: narrower loader API, registry-only validation ownership, explicit provenance handoff, and focused node-system regression updates.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_registry_validation.py tests/test_registry_filters.py tests/test_node_package_io_ops.py --ignore=venv -q`
- Non-goals: no runtime compiler stage split beyond adapter shims, no QML or shell changes.
- Packetization notes: likely `P03`; can land in parallel with `T01` and most of `T02`, then act as an input contract for `T05`.

### T04 Workspace and Runtime Contract Cleanup
- Primary source subagent: `workspace-contracts`
- Primary regression subagent: `verification-control-plane`
- Goal: move workspace ordering, active-workspace ownership, and shared runtime DTO contracts behind one narrow coordination layer so graph, persistence, execution, and shell code stop carrying slightly different workspace assumptions.
- Preconditions: `T01`, `T02`
- Conservative write scope: `ea_node_editor/workspace/manager.py`, `ea_node_editor/workspace/ownership.py`, `ea_node_editor/runtime_contracts/*.py`, direct callers in `ea_node_editor/graph` and `ea_node_editor/ui/shell`, `tests/test_workspace_manager.py`, `tests/test_workspace_library_controller_unit.py`, `tests/main_window_shell/bridge_contracts_workspace_and_console.py`, `tests/main_window_shell/shell_runtime_contracts.py`
- Deliverables: explicit workspace coordination API, cleaned shared DTO contracts, adoption in direct callers, and focused workspace/runtime regression updates.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/test_workspace_manager.py tests/test_workspace_library_controller_unit.py tests/main_window_shell/bridge_contracts_workspace_and_console.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`
- Non-goals: no shell composition rewrite yet, no execution assembly rewrite yet, no packaging updates.
- Packetization notes: likely `P04`; should land before broad UI adoption so `T05` and `T06` can depend on one workspace/runtime contract.

### T05 Execution Pipeline Stage Split
- Primary source subagent: `execution-pipeline`
- Primary regression subagent: `verification-control-plane`
- Goal: split compiler flattening, subnode expansion, and runtime snapshot assembly into explicit stages with one authority for workspace metadata normalization.
- Preconditions: `T02`, `T03`, `T04`
- Conservative write scope: `ea_node_editor/execution/compiler.py`, `ea_node_editor/execution/runtime_snapshot_assembly.py`, `ea_node_editor/execution/runtime_snapshot.py`, adjacent runtime snapshot models/helpers under `ea_node_editor/execution`, `tests/test_execution_artifact_refs.py`, `tests/test_execution_handle_refs.py`, `tests/test_execution_worker.py`, `tests/test_execution_viewer_protocol.py`, `tests/test_passive_runtime_wiring.py`
- Deliverables: staged runtime build pipeline, extracted normalization helpers, narrower compiler input/output contracts, and focused execution regression updates.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py tests/test_execution_worker.py tests/test_execution_viewer_protocol.py tests/test_passive_runtime_wiring.py --ignore=venv -q`
- Non-goals: no viewer transport rewrite, no packaging-profile redesign, no QML bridge rewiring.
- Packetization notes: likely `P05`; consume upstream contracts from `T02` through `T04` rather than reopening persistence or node-loader ownership.

### T06 Shell Composition and Graph-Scene Bridge Adoption
- Primary source subagent: `ui-shell-qml`
- Primary regression subagent: `verification-control-plane`
- Goal: replace monolithic shell wiring with feature-owned bridge seams, harden `graph_scene_bridge` as an editor-engine boundary instead of generic presentation code, and shrink or eliminate legacy canvas adapter paths where direct state/command bridges already cover the contract.
- Preconditions: `T01`, `T04`, `T05`
- Conservative write scope: `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui/shell/context_bridges.py`, `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/graph_canvas_bridge.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`, `tests/test_main_window_shell.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_graph_surface_input_contract.py`, `tests/graph_surface_pointer_regression.py`, `tests/main_window_shell/bridge_contracts_graph_canvas.py`, `tests/main_window_shell/bridge_qml_boundaries.py`
- Deliverables: feature-owned bridge registration, narrower composition root, cleaner graph-scene/editor boundary, reduced legacy adapter surface, and focused shell/QML regression updates.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py tests/graph_surface_pointer_regression.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`
- Non-goals: no new user-facing workflow features, no presentation redesign, no packaging or verification-manifest ownership changes.
- Packetization notes: likely `P06`; if the write scope grows, split shell composition and graph-scene adoption into adjacent packets without reopening core contracts.

### T07 Verification, Packaging, and Traceability Closeout
- Primary source subagent: `verification-control-plane`
- Primary regression subagent: `verification-control-plane`
- Goal: update path-based verification manifests, packaging assertions, and architecture-traceability docs so the repo's enforcement surface matches the refactored module layout.
- Preconditions: `T01`, `T02`, `T03`, `T04`, `T05`, `T06`
- Conservative write scope: `scripts/verification_manifest.py`, `ea_node_editor/pytest_defaults.py`, `pyproject.toml`, `tests/conftest.py`, `ea_node_editor.spec`, `ARCHITECTURE.md`, `README.md`, `tests/test_pytest_defaults.py`, `tests/test_run_verification.py`, `tests/test_packaging_configuration.py`, `tests/test_architecture_boundaries.py`, `tests/test_traceability_checker.py`, `tests/test_markdown_hygiene.py`, `tests/test_dead_code_hygiene.py`
- Deliverables: synchronized verification catalog, updated packaging/traceability assertions, refreshed architecture references, and final refactor closeout coverage.
- Verification: `.\venv\Scripts\python.exe -m pytest tests/test_pytest_defaults.py tests/test_run_verification.py tests/test_packaging_configuration.py tests/test_architecture_boundaries.py tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_dead_code_hygiene.py --ignore=venv -q`
- Non-goals: no new behavior features, no reopening of earlier subsystem boundaries unless a failing traceability rule proves the plan missed a necessary move.
- Packetization notes: likely `P07`; this is the final closeout slice and should absorb path or ownership fallout from earlier tasks instead of pushing it back upstream.

## Work Packet Conversion Map
1. `P00 Bootstrap`: create the packet manifest, status ledger, prompt files, allowlist entries, and packet index registration while treating this plan file as the review baseline.
2. `P01 Graph State and Mutation Boundary`: derived primarily from `T01` and owned by `graph-core`.
3. `P02 Persistence Document and Overlay Boundary`: derived primarily from `T02` and owned by `persistence-stack`.
4. `P03 Node Registry and Plugin Loading Boundary`: derived primarily from `T03` and owned by `nodes-system`.
5. `P04 Workspace and Runtime Contract Cleanup`: derived primarily from `T04` and owned by `workspace-contracts`.
6. `P05 Execution Pipeline Stage Split`: derived primarily from `T05` and owned by `execution-pipeline`.
7. `P06 Shell Composition and Graph-Scene Bridge Adoption`: derived primarily from `T06` and owned by `ui-shell-qml`.
8. `P07 Verification, Packaging, and Traceability Closeout`: derived primarily from `T07` and owned by `verification-control-plane`.

## Test Plan
- Graph-core boundary regression: `tests/test_port_locking.py`, `tests/test_comment_backdrop_membership.py`, `tests/graph_track_b/scene_model_graph_model_suite.py`
- Persistence boundary regression: `tests/test_serializer.py`, `tests/test_serializer_schema_migration.py`, `tests/test_project_artifact_resolution.py`, `tests/test_project_artifact_store.py`
- Node-system regression: `tests/test_plugin_loader.py`, `tests/test_registry_validation.py`, `tests/test_registry_filters.py`, `tests/test_node_package_io_ops.py`
- Workspace/runtime regression: `tests/test_workspace_manager.py`, `tests/test_workspace_library_controller_unit.py`, `tests/main_window_shell/bridge_contracts_workspace_and_console.py`, `tests/main_window_shell/shell_runtime_contracts.py`
- Execution regression: `tests/test_execution_artifact_refs.py`, `tests/test_execution_handle_refs.py`, `tests/test_execution_worker.py`, `tests/test_execution_viewer_protocol.py`, `tests/test_passive_runtime_wiring.py`
- Shell/QML regression: `tests/test_main_window_shell.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_graph_surface_input_contract.py`, `tests/graph_surface_pointer_regression.py`, `tests/main_window_shell/bridge_contracts_graph_canvas.py`, `tests/main_window_shell/bridge_qml_boundaries.py`
- Control-plane closeout: `tests/test_pytest_defaults.py`, `tests/test_run_verification.py`, `tests/test_packaging_configuration.py`, `tests/test_architecture_boundaries.py`, `tests/test_traceability_checker.py`, `tests/test_markdown_hygiene.py`, `tests/test_dead_code_hygiene.py`

## Assumptions
- This refactor preserves current user-facing behavior and existing project/document formats unless a later feature plan explicitly changes them.
- `graph` plus `persistence` is the highest-risk seam, so `T01` and `T02` intentionally happen before execution and UI adoption work.
- Path-driven verification and packaging assertions are part of the contract in this repo, so file moves are not complete until `T07` updates the control plane.
- The named subagents are planning handles for future worker packets; a later packetization pass can merge adjacent tasks only when it does not widen a stable subsystem seam.
