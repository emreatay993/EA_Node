# P10 Plugin Add-on Descriptor Only Wrap-up

## Implementation Summary

- Packet: `P10`
- Branch Label: `codex/corex-no-legacy-architecture-cleanup/p10-plugin-addon-descriptor-only`
- Commit Owner: `worker`
- Commit SHA: `b291c9e09ed18a0093d3189063c694038b2b0241`
- Changed Files: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P10_plugin_addon_descriptor_only_WRAPUP.md`, `ea_node_editor/addons/ansys_dpf/__init__.py`, `ea_node_editor/addons/ansys_dpf/catalog.py`, `ea_node_editor/addons/catalog.py`, `ea_node_editor/addons/hot_apply.py`, `ea_node_editor/nodes/builtins/ansys_dpf.py`, `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`, `ea_node_editor/nodes/builtins/ansys_dpf_helper_catalog.py`, `ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py`, `ea_node_editor/nodes/package_manager.py`, `ea_node_editor/nodes/plugin_loader.py`, `tests/test_dpf_viewer_node.py`, `tests/test_package_manager.py`, `tests/test_plugin_loader.py`
- Artifacts Produced: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P10_plugin_addon_descriptor_only_WRAPUP.md`

Implemented descriptor-only plugin loading by removing legacy plugin class probing, tuple shorthand descriptor coercion, synthetic namespace package creation, and importlib metadata entry-point compatibility branching. Plugin modules, package modules, entry-point targets, and add-on backend modules now expose explicit descriptor records or backend descriptor records.

Package manifests now require explicit `name` metadata, including installed package listing. DPF descriptor authority moved to the canonical add-on catalog, with dynamic DPF descriptor `__getattr__` forwarding removed from packet-owned modules. Add-on enabled-state persistence is split from hot-apply runtime rebuild orchestration through `persist_addon_enabled_state()` and `rebuild_hot_apply_runtime()`.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py tests/test_registry_validation.py tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py tests/test_execution_viewer_service.py --ignore=venv -q` (`99 passed, 32 warnings, 5 subtests passed`)

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py --ignore=venv -q` (`33 passed`)

- PASS: `git diff --check`

- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing.

1. Launch the app from this branch with the project venv and open the Add-ons manager.
   Expected result: the ANSYS DPF add-on appears under its canonical add-on identity and toggling it persists enabled state without crashing the shell.

2. With `ansys.dpf.core` installed, disable and re-enable the ANSYS DPF add-on.
   Expected result: disabling rebuilds the registry so DPF nodes are unavailable in the current session; re-enabling rebuilds the registry and restores the DPF node family for new graph edits.

3. Import or export a small `.eanp` package whose `node_package.json` includes an explicit `name` and whose plugin module exposes `PluginDescriptor` records.
   Expected result: valid descriptor-backed packages import/export successfully; packages missing explicit manifest names or descriptor records are rejected.

## Residual Risks

- Hot-apply runtime rebuild orchestration remains centralized in `rebuild_hot_apply_runtime()` because the current shell, graph scene, worker services, and viewer host call sites still pass runtime targets to the add-on apply operation. Persistence is now separately testable, but the runtime rebuild helper still coordinates these targets.
- Live graph-scene rebuilds still rely on current registry normalization behavior for disabled add-on nodes; unavailable add-on visual placeholder projection is not broadened beyond the packet-owned hot-apply test adjustment.
- Packet-owned add-on lookup rejects `ansys.dpf` and `ansys_dpf` aliases; any remaining UI focus-token convenience outside the conservative P10 write scope was not edited in this packet.

## Ready for Integration

- Yes: P10 source and packet-owned tests are committed, required verification and review gate pass, and residual hot-apply coupling is documented for downstream integration review.
