# ADDON_MANAGER_BACKEND_PREPARATION P06: DPF Hot Apply Registry And Runtime Rebuild

## Objective

- Support in-session enable/disable for the DPF add-on by rebuilding registries, worker/runtime services, and viewer wiring so existing DPF nodes relock when disabled and rebind when re-enabled.

## Preconditions

- `P00` is marked `PASS`.
- `P01` is marked `PASS`.
- `P03` is marked `PASS`.
- `P05` is marked `PASS`.
- No later `ADDON_MANAGER_BACKEND_PREPARATION` packet is in progress.

## Execution Dependencies

- `P00`
- `P01`
- `P03`
- `P05`

## Target Subsystems

- `ea_node_editor/addons/**`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/execution/worker_services.py`
- `ea_node_editor/execution/dpf_runtime_service.py`
- `ea_node_editor/execution/viewer_backend_dpf.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/dpf_viewer_widget_binder.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_viewer_host_service.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_dpf_viewer_widget_binder.py`

## Conservative Write Scope

- `ea_node_editor/addons/**`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/execution/worker_services.py`
- `ea_node_editor/execution/dpf_runtime_service.py`
- `ea_node_editor/execution/viewer_backend_dpf.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/dpf_viewer_widget_binder.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_viewer_host_service.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_dpf_viewer_widget_binder.py`
- `docs/specs/work_packets/addon_manager_backend_preparation/P06_dpf_hot_apply_registry_and_runtime_rebuild_WRAPUP.md`

## Required Behavior

- Implement rebuild-based apply for `hot_apply` add-ons using DPF as the first supported add-on.
- Disabling DPF must remove DPF descriptors from the live registry, refresh the node library, and cause existing DPF nodes to present the locked placeholder path from `P03`.
- Re-enabling DPF must rebuild the live registry/services and restore saved DPF nodes to normal live-node behavior without project loss.
- Clear or rebuild DPF-specific runtime, viewer, and binder caches so stale DPF objects do not survive the toggle.
- Keep `restart_required` add-ons on the persisted pending-restart path from `P01`; do not generalize true in-session unload beyond DPF here.

## Non-Goals

- No final Add-On Manager layout yet; that belongs to `P07`.
- No non-DPF hot-apply support beyond the generic contract needed for DPF.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_execution_viewer_service.py tests/test_viewer_host_service.py tests/test_dpf_viewer_node.py tests/test_dpf_viewer_widget_binder.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_viewer_host_service.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/addon_manager_backend_preparation/P06_dpf_hot_apply_registry_and_runtime_rebuild_WRAPUP.md`

## Acceptance Criteria

- DPF can be toggled off in-session and existing DPF nodes become locked placeholders rather than vanishing.
- DPF can be toggled back on in-session and saved nodes rebind to live behavior.
- Stale runtime/viewer/binder state does not survive the toggle.
- The inherited DPF runtime and viewer regression anchors pass.

## Handoff Notes

- `P07` depends on this packet for live DPF toggle validation inside the manager UI. Keep the hot-apply contract generic enough for later non-DPF `hot_apply` add-ons without widening this packet into a second add-on migration.
