# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P09: Nodes SDK Registry

## Objective

Make node SDK, descriptor, registry validation, taxonomy, and node authoring facades explicit while keeping runtime and UI implementation details out of node contracts.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and node SDK/registry tests needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P08_passive_viewer_overlays` is `PASS`.

## Execution Dependencies

- `P08_passive_viewer_overlays`

## Target Subsystems

- Node SDK facades
- Node types and plugin contracts
- Registry validation
- Builtin taxonomy and descriptor normalization
- Node SDK/registry tests

## Conservative Write Scope

- `ea_node_editor/execution/runtime_snapshot_assembly.py`
- `ea_node_editor/nodes/**`
- `tests/test_plugin_loader.py`
- `tests/test_registry_validation.py`
- `tests/test_package_manager.py`
- `tests/test_dpf_library_taxonomy.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_architecture_boundaries.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_P09_nodes_sdk_registry.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P09_nodes_sdk_registry_WRAPUP.md`

## Required Behavior

- Keep `ea_node_editor.nodes.types` as the SDK hub and `ea_node_editor.nodes` as a thin authoring facade.
- Keep `nodes` focused on declarative metadata, descriptors, taxonomy, registry validation, and stable node authoring APIs.
- Remove or guard node-side dependencies on execution/UI implementation details.
- Preserve descriptor-first loading, DPF taxonomy behavior, package validation behavior, and public node SDK exports.

## Non-Goals

- Do not move add-on enablement or hot-apply orchestration; that is `P10`.
- Do not change runtime execution semantics.
- Do not remove intentional import-only SDK facades without compatibility handling.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_registry_validation.py tests/test_package_manager.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_dpf_library_taxonomy.py tests/test_dpf_node_catalog.py tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P09_nodes_sdk_registry_WRAPUP.md`

## Acceptance Criteria

- Node SDK and registry ownership is explicit and guarded.
- Descriptor-first node behavior and DPF taxonomy behavior remain compatible.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If `nodes/plugin_loader.py` still contains add-on-specific discovery after this packet, record it as a planned handoff to `P10`.

User-authorized scope extension: `ea_node_editor/execution/runtime_snapshot_assembly.py` is included to fix the architecture boundary failure discovered during P09 verification.
