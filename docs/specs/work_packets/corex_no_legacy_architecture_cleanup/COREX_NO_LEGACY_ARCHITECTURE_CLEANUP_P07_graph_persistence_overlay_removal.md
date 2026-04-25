# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P07: Graph Persistence Overlay Removal

## Objective

- Remove unresolved persistence overlay state from graph-owned models and normalization now that persistence accepts only current shapes.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only graph/persistence/tests needed for this packet

## Preconditions

- `P06` is marked `PASS`.

## Execution Dependencies

- `P06`

## Target Subsystems

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/file_issue_state.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/file_issues.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_registry_validation.py`
- `tests/test_serializer.py`
- `tests/test_project_file_issues.py`
- `tests/test_workspace_manager.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P07_graph_persistence_overlay_removal_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/file_issue_state.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/file_issues.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_registry_validation.py`
- `tests/test_serializer.py`
- `tests/test_project_file_issues.py`
- `tests/test_workspace_manager.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P07_graph_persistence_overlay_removal_WRAPUP.md`

## Required Behavior

- Remove `WorkspaceData.unresolved_*_docs`, `authored_node_overrides`, graph-level persistence capture/restore helpers, and normalization paths that preserve missing-add-on authored payloads through graph core.
- Remove `_rebind_resolved_unresolved_content` and missing-add-on placeholder rebinding from graph normalization unless a current feature still uses it without legacy persistence.
- Keep graph model semantics for current live nodes/edges, passive nodes, comment backdrops, hierarchy, and managed-file references.
- Move any still-needed unavailable-add-on UI projection to a dedicated add-on/viewer layer instead of graph model sidecars, or explicitly defer that to P10/P12 if it cannot be removed safely in this packet.
- Update boundary tests so graph no longer imports or exposes persistence overlay state as a compatibility seam.

## Non-Goals

- No graph mutation API consolidation; that belongs to `P08`.
- No plugin descriptor cleanup; that belongs to `P10`.
- No viewer transport cleanup; that belongs to `P12`.

## Verification Commands

1. `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py tests/test_serializer.py tests/test_project_file_issues.py tests/test_workspace_manager.py --ignore=venv -q`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P07_graph_persistence_overlay_removal_WRAPUP.md`

## Acceptance Criteria

- Graph-owned models do not carry persistence overlay sidecars.
- Current projects still load/save through the canonical serializer.
- Boundary tests assert graph-domain purity without compatibility overlay imports.

## Handoff Notes

- `P08` can simplify graph mutation and fragment code after graph persistence sidecars are removed.
