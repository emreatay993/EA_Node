# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P10: Plugin Add-On Descriptor

## Objective

Split generic plugin/node discovery from add-on registration, enablement, cache invalidation, hot-apply policy, and runtime rebuild orchestration.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and plugin/add-on tests needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P09_nodes_sdk_registry` is `PASS`.

## Execution Dependencies

- `P09_nodes_sdk_registry`

## Target Subsystems

- Add-on catalog and hot-apply orchestration
- Plugin loader add-on discovery seams
- Package manager validation where it crosses add-on descriptors
- DPF add-on catalogs and cache behavior

## Conservative Write Scope

- `ea_node_editor/addons/**`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/package_manager.py`
- `tests/test_plugin_loader.py`
- `tests/test_package_manager.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_viewer_node.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P10_plugin_addon_descriptor_WRAPUP.md`

## Required Behavior

- Keep generic plugin descriptor discovery in node/plugin code.
- Move add-on record discovery, add-on backend loading, enablement state, and hot-apply policy to add-on-owned surfaces.
- Put runtime rebuild calls behind a runtime/application coordinator instead of direct add-on knowledge of every service where feasible.
- Preserve descriptor-only loading and DPF add-on catalog behavior.

## Non-Goals

- Do not change public node SDK exports owned by `P09` unless compatibility requires a small adapter.
- Do not introduce class probing or constructor fallback.
- Do not change runtime worker behavior except through coordinator handoff.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P10_plugin_addon_descriptor_WRAPUP.md`

## Acceptance Criteria

- Add-on policy and node discovery are separated without reviving legacy plugin paths.
- DPF add-on registration, enablement, and descriptor behavior remain compatible.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If a runtime coordinator extraction overlaps `P11`, keep this packet to add-on-facing adapter boundaries and record the handoff.
