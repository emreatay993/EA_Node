# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P08: Graph Mutation and Fragment Consolidation

## Objective

- Collapse duplicated graph mutation, payload parsing, fragment remapping, and facade aliases onto one authoritative graph-domain API.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only graph/test files needed for this packet

## Preconditions

- `P07` is marked `PASS`.

## Execution Dependencies

- `P07`

## Target Subsystems

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/rules.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/transform_fragment_ops.py`
- `ea_node_editor/graph/transform_grouping_ops.py`
- `ea_node_editor/graph/transform_layout_ops.py`
- `ea_node_editor/graph/transform_subnode_ops.py`
- `ea_node_editor/graph/__init__.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_registry_validation.py`
- `tests/test_workspace_manager.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_serializer.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P08_graph_mutation_and_fragment_consolidation_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/rules.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/transform_fragment_ops.py`
- `ea_node_editor/graph/transform_grouping_ops.py`
- `ea_node_editor/graph/transform_layout_ops.py`
- `ea_node_editor/graph/transform_subnode_ops.py`
- `ea_node_editor/graph/__init__.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_registry_validation.py`
- `tests/test_workspace_manager.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_serializer.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P08_graph_mutation_and_fragment_consolidation_WRAPUP.md`

## Required Behavior

- Choose one graph write authority for packet-owned mutations, then remove duplicate public write routes in `GraphModel`, `ValidatedGraphMutation`, and `WorkspaceMutationService` where they only forward or bypass invariants.
- Centralize node/edge payload parsing for live persistence and graph fragments; remove duplicated coercion in fragment helpers.
- Remove encoded external-parent fragment conventions and shell-pin remapping branches unless current copy/paste semantics still require them with packet-owned proof.
- Collapse module-level pass-through aliases in `normalization.py`, `rules.py`, `transforms.py`, and `graph/__init__.py` onto one intentional public facade or direct imports.
- Keep hierarchy, duplicate/copy/paste, comment-backdrop containment, passive flow edges, and serializer round-trip behavior intact for current projects.

## Non-Goals

- No persistence schema changes; P06/P07 own those.
- No node registry/category cleanup; P09 owns that.
- No broad performance refactor.

## Verification Commands

1. `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py tests/test_workspace_manager.py tests/test_passive_runtime_wiring.py tests/test_serializer.py --ignore=venv -q`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P08_graph_mutation_and_fragment_consolidation_WRAPUP.md`

## Acceptance Criteria

- Packet-owned graph writes pass through one authoritative mutation/invariant path.
- Live persistence and fragment import/export reuse one parser/serializer contract.
- Graph facade modules no longer exist only as compatibility aliases.

## Handoff Notes

- `P09` can assume graph model payload shapes are current and no longer need registry compatibility aliasing for old documents.
