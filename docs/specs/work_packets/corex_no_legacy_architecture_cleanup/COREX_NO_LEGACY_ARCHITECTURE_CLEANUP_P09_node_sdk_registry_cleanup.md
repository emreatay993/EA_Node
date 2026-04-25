# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P09: Node SDK Registry Cleanup

## Objective

- Remove node SDK and registry compatibility paths that preserve flat categories, class-first built-ins, and broad internal import shims.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only node SDK/registry files needed for this packet

## Preconditions

- `P08` is marked `PASS`.

## Execution Dependencies

- `P08`

## Target Subsystems

- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/node_specs.py`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/decorators.py`
- `ea_node_editor/nodes/builtins/core.py`
- `ea_node_editor/nodes/builtins/hpc.py`
- `ea_node_editor/nodes/builtins/integrations*.py`
- `ea_node_editor/nodes/builtins/passive_*.py`
- `ea_node_editor/nodes/builtins/subnode.py`
- `tests/test_registry_validation.py`
- `tests/test_registry_filters.py`
- `tests/test_passive_node_contracts.py`
- `tests/test_port_labels.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_refs.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P09_node_sdk_registry_cleanup_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/node_specs.py`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/decorators.py`
- `ea_node_editor/nodes/builtins/core.py`
- `ea_node_editor/nodes/builtins/hpc.py`
- `ea_node_editor/nodes/builtins/integrations*.py`
- `ea_node_editor/nodes/builtins/passive_*.py`
- `ea_node_editor/nodes/builtins/subnode.py`
- `tests/test_registry_validation.py`
- `tests/test_registry_filters.py`
- `tests/test_passive_node_contracts.py`
- `tests/test_port_labels.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_refs.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P09_node_sdk_registry_cleanup_WRAPUP.md`

## Required Behavior

- Make `category_path` the only registry/category contract; remove descendant matching through legacy flat `category` aliases.
- Convert built-in registration away from class-first plugin factories toward descriptor records or focused descriptor tables where feasible inside this packet.
- Remove node serialization compatibility that accepts missing current fields, such as old `port_labels` absence, unless the field is optional in the current schema by design.
- Narrow `ea_node_editor.nodes.types` to a curated public SDK surface, and migrate in-repo internals to focused modules.
- Keep current built-in node IDs, port IDs, runtime behavior, passive families, and serializer output stable unless a retired compatibility field is explicitly removed.

## Non-Goals

- No third-party plugin loader/add-on discovery cleanup; that belongs to `P10`.
- No DPF alias-module cleanup; that belongs to `P10`.
- No docs/README SDK wording updates; that belongs to `P14`.

## Verification Commands

1. `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py tests/test_registry_filters.py tests/test_passive_node_contracts.py tests/test_port_labels.py tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py --ignore=venv -q`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py tests/test_registry_filters.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P09_node_sdk_registry_cleanup_WRAPUP.md`

## Acceptance Criteria

- Registry filtering and node authoring use `category_path` only.
- Built-in node registration has a descriptor-first shape or a documented remaining migration edge in the wrap-up.
- Tests no longer assert legacy category or missing-field compatibility.

## Handoff Notes

- `P10` inherits the descriptor-first expectation and should remove plugin/add-on compatibility loaders on top of it.
