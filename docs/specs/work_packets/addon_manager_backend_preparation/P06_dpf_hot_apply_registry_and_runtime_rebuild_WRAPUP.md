## Implementation Summary
- Packet: `P06`
- Branch Label: `codex/addon-manager-backend-preparation/p06-dpf-hot-apply-registry-and-runtime-rebuild`
- Commit Owner: `worker`
- Commit SHA: `b24def0fbc0ad52a97417184616085f3f6e00309`
- Changed Files:
  - `ea_node_editor/addons/__init__.py`
  - `ea_node_editor/addons/ansys_dpf/catalog.py`
  - `ea_node_editor/addons/catalog.py`
  - `ea_node_editor/addons/hot_apply.py`
  - `ea_node_editor/execution/worker_services.py`
  - `ea_node_editor/nodes/bootstrap.py`
  - `ea_node_editor/ui_qml/graph_scene_bridge.py`
  - `ea_node_editor/ui_qml/viewer_host_service.py`
  - `tests/test_dpf_runtime_service.py`
  - `tests/test_dpf_viewer_node.py`
  - `tests/test_execution_viewer_service.py`
  - `tests/test_viewer_host_service.py`
  - `docs/specs/work_packets/addon_manager_backend_preparation/P06_dpf_hot_apply_registry_and_runtime_rebuild_WRAPUP.md`
- Artifacts Produced:
  - `docs/specs/work_packets/addon_manager_backend_preparation/P06_dpf_hot_apply_registry_and_runtime_rebuild_WRAPUP.md`
  - `ea_node_editor/addons/hot_apply.py`

Implemented a packet-local hot-apply backend seam that persists add-on state, rebuilds the live node registry for `hot_apply` add-ons, and keeps `restart_required` add-ons on the pending-restart path. DPF is now the first live add-on wired through that seam: disabling it removes its descriptors from rebuilt registries, invalidates runtime and viewer transport state, drops the embedded viewer binder/backend, and normalizes open graph content into the P03 locked placeholder path; re-enabling rebuilds the same registry and service layers so DPF nodes bind back to live behavior without project loss.

## Verification
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_execution_viewer_service.py tests/test_viewer_host_service.py tests/test_dpf_viewer_node.py tests/test_dpf_viewer_widget_binder.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_viewer_host_service.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives
Too soon for manual testing

- The packet lands the backend apply seam, registry rebuild, graph normalization, and runtime/viewer cache invalidation, but there is still no packet-owned UI in this branch that invokes the toggle end to end.
- The next useful manual milestone is P07, where the Add-On Manager surface can call `apply_addon_enabled_state(...)` and feed the rebuilt registry back into the shell library presenter.
- Until that UI hook exists, the automated packet regressions are the reliable validation for disable -> placeholder, disable -> cache teardown, and re-enable -> live restore.

## Residual Risks
- Shell library refresh still depends on the caller wiring the `on_registry_rebuilt` callback into the live library presenter; this packet prepares that seam but does not own the P07 UI integration.
- `WorkerServices.rebuild_addon_runtime(...)` invalidates the worker handle registry to guarantee stale DPF objects do not survive the toggle, so any live runtime handles in that worker are intentionally discarded during the rebuild.

## Ready for Integration
Yes: the packet-owned backend seam, graph normalization path, and DPF runtime/viewer/binder rebuild coverage are in place, and both the required verification command and review gate pass on the packet branch.
