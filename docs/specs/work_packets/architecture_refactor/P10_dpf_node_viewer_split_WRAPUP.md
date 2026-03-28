# P10 DPF Node Viewer Split Wrap-Up

## Implementation Summary

- Packet: `P10`
- Branch Label: `codex/architecture-refactor/p10-dpf-node-viewer-split`
- Commit Owner: `worker`
- Commit SHA: `5fc7ee23629a57b050f82c1a4a744468289ac5e9`
- Changed Files: `ea_node_editor/nodes/builtins/ansys_dpf.py`, `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`, `ea_node_editor/nodes/builtins/ansys_dpf_compute.py`, `ea_node_editor/nodes/builtins/ansys_dpf_node_helpers.py`, `ea_node_editor/nodes/builtins/ansys_dpf_viewer.py`, `ea_node_editor/nodes/builtins/ansys_dpf_viewer_adapter.py`, `ea_node_editor/nodes/package_manager.py`, `ea_node_editor/nodes/plugin_loader.py`, `tests/test_dpf_node_catalog.py`, `tests/test_execution_viewer_protocol.py`, `tests/test_package_manager.py`, `tests/test_plugin_loader.py`, `docs/specs/work_packets/architecture_refactor/P10_dpf_node_viewer_split_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/architecture_refactor/P10_dpf_node_viewer_split_WRAPUP.md`, `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`, `ea_node_editor/nodes/builtins/ansys_dpf_compute.py`, `ea_node_editor/nodes/builtins/ansys_dpf_node_helpers.py`, `ea_node_editor/nodes/builtins/ansys_dpf_viewer.py`, `ea_node_editor/nodes/builtins/ansys_dpf_viewer_adapter.py`

Split the DPF built-in surface into compute, viewer, catalog, helper, and viewer-adapter modules while keeping `ea_node_editor/nodes/builtins/ansys_dpf.py` as the compatibility export surface for existing imports. The viewer node no longer imports execution protocol command/event types directly; that edge now lives in the thin `ansys_dpf_viewer_adapter.py` allowance module.

Finished the packet-owned package discovery cleanup by exposing `plugin_loader.discover_package_plugins()` and moving `package_manager` off the private loader helper. Added regression coverage for the descriptor-first DPF catalog, the viewer protocol ownership seam, the public package discovery API, and the package manager’s public discovery dependency.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_dpf_compute_nodes.py tests/test_dpf_viewer_node.py tests/test_execution_viewer_protocol.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_package_manager.py tests/test_plugin_loader.py tests/test_node_package_io_ops.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_dpf_viewer_node.py tests/test_package_manager.py tests/test_plugin_loader.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Viewer session smoke: with `ansys.dpf.core` and `pyvista` available in the repo `venv`, run a graph that feeds a known `.rst` file into `DPF Model`, `DPF Result Field`, and `DPF Viewer`. Expected result: the viewer node opens a session, the viewer summary shows the expected result name and set label, and the node still behaves like the pre-split `dpf.viewer` surface.
2. Viewer reopen policy smoke: rerun the same graph once with the default `viewer_live_policy=focus_only` and once with `viewer_live_policy=keep_live`. Expected result: both runs preserve the cached summary on reopen, `focus_only` still enforces single-live behavior, and `keep_live` still keeps the session eligible for reopen from proxy/live state.
3. Node package discovery smoke: export a simple node package with one discoverable top-level plugin module, then import it through the app’s node package flow. Expected result: the package installs without a manifest-node mismatch warning and the declared node type appears in the node library immediately after reload.

## Residual Risks

Manual smoke coverage for the DPF viewer path still depends on optional local `ansys.dpf.core` and `pyvista` availability plus a runnable UI session; this packet validated the split with automated regression coverage but did not rerun a packaged-shell viewer smoke.

## Ready for Integration

- Yes: the DPF node/catalog/viewer split and the public package-discovery seam are committed on the packet branch with the packet verification commands and review gate passing.
