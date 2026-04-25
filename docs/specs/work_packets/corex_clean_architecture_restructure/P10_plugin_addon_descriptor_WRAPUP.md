# P10 Plugin Add-On Descriptor Wrap-Up

## Implementation Summary

- Packet: P10_plugin_addon_descriptor
- Branch Label: codex/corex-clean-architecture-restructure/p10-plugin-addon-descriptor
- Commit Owner: worker
- Commit SHA: d6fb309606bb209b7dbccb35ecf746c33ffa0626
- Changed Files: docs/specs/work_packets/corex_clean_architecture_restructure/P10_plugin_addon_descriptor_WRAPUP.md, ea_node_editor/addons/__init__.py, ea_node_editor/addons/catalog.py, ea_node_editor/addons/hot_apply.py, ea_node_editor/nodes/bootstrap.py, ea_node_editor/nodes/plugin_loader.py, tests/test_plugin_loader.py
- Artifacts Produced: docs/specs/work_packets/corex_clean_architecture_restructure/P10_plugin_addon_descriptor_WRAPUP.md

Moved add-on record discovery, add-on backend loading, enablement filtering, node-backend selection, and cache invalidation into `ea_node_editor.addons.catalog`. `nodes.plugin_loader` now keeps generic plugin descriptor discovery and compatibility delegates for out-of-scope callers.

Added an add-on runtime rebuild coordinator boundary in `ea_node_editor.addons.hot_apply`, preserving existing graph scene, worker service, viewer host, callback, descriptor-only plugin, and DPF catalog behavior. `nodes.bootstrap` now consumes add-on-owned backend collections instead of importing and special-casing add-on modules directly.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py --ignore=venv`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py --ignore=venv`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py --ignore=venv`
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing.

- Prerequisites: Use this branch with the project venv available. For the DPF toggle path, `ansys.dpf.core` must be installed so the ANSYS DPF add-on is available.
- Action: Launch the app with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`, open the add-on manager, and inspect the ANSYS DPF row. Expected result: the row loads from add-on-owned catalog records and shows availability, enabled state, version, and provided node data without plugin-loader errors.
- Action: If ANSYS DPF is available, disable and re-enable it from the add-on manager. Expected result: the change hot-applies without requiring restart, the registry/viewer runtime is rebuilt through the coordinator boundary, and DPF nodes are hidden while disabled and available again after re-enable.
- Action: Install or load a descriptor-only node plugin/package through the existing plugin/package workflow. Expected result: descriptor-only plugin loading still works independently of add-on enablement.

## Residual Risks

- Full cross-application runtime coordinator extraction remains a P11 handoff. P10 keeps the change to add-on-facing adapter boundaries while preserving existing service calls behind the coordinator object.
- Verification reported existing Ansys DPF deprecation warnings and non-fatal Windows pytest temp cleanup `PermissionError` messages after successful pytest exits.

## Ready for Integration

- Yes: Required verification and the listed review gate passed, and the final changed-file set is confined to the P10 conservative write scope plus this packet wrap-up artifact.
