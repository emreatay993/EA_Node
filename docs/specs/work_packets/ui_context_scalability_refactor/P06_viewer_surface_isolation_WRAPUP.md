## Implementation Summary
- Packet: `P06`
- Branch Label: `codex/ui-context-scalability-refactor/p06-viewer-surface-isolation`
- Commit Owner: `worker`
- Commit SHA: `caf906f3be267849df42b7ff385ec3a448d50b8e`
- Changed Files: `docs/specs/work_packets/ui_context_scalability_refactor/P06_viewer_surface_isolation_WRAPUP.md`, `ea_node_editor/execution/viewer_session_service.py`, `ea_node_editor/execution/viewer_session_service_support.py`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurfaceContent.qml`, `ea_node_editor/ui_qml/viewer_session_bridge.py`, `ea_node_editor/ui_qml/viewer_session_bridge_support.py`, `tests/test_execution_viewer_service.py`, `tests/test_viewer_session_bridge.py`, `tests/test_viewer_surface_contract.py`
- Artifacts Produced: `docs/specs/work_packets/ui_context_scalability_refactor/P06_viewer_surface_isolation_WRAPUP.md`, `ea_node_editor/execution/viewer_session_service.py`, `ea_node_editor/execution/viewer_session_service_support.py`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurfaceContent.qml`, `ea_node_editor/ui_qml/viewer_session_bridge.py`, `ea_node_editor/ui_qml/viewer_session_bridge_support.py`, `tests/test_execution_viewer_service.py`, `tests/test_viewer_session_bridge.py`, `tests/test_viewer_surface_contract.py`

Reduced the packet-capped entrypoints to thin viewer-only facades: `viewer_session_service.py` now re-exports the viewer session model builders and service from `viewer_session_service_support.py`, `viewer_session_bridge.py` now re-exports the Qt bridge from `viewer_session_bridge_support.py`, and `GraphViewerSurface.qml` now delegates the full viewer surface implementation to `GraphViewerSurfaceContent.qml`.

Added regression anchors that enforce the P06 line-budget contract and the new isolation seam so later packets keep the public viewer service, bridge, and surface entrypoints small while viewer-specific projection and surface logic stays behind dedicated viewer-only support files.

## Verification
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_viewer_surface_contract.py tests/test_viewer_surface_host.py tests/test_dpf_viewer_node.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives
Ready for manual testing
- Prerequisite: start the desktop app on a machine with the normal viewer stack available and open a graph containing at least one wired `DPF Viewer` node that can materialize a session.
- Open and close smoke: open the viewer session from the node surface, then close it from the same surface. Expected result: the viewer status strip moves through `Opening` or `Live` and back to the closed placeholder without missing controls or stale overlay state.
- Focus-demotion smoke: open two viewer sessions with the default focus-only behavior, then change selection from the first viewer node to the second. Expected result: the previously focused node demotes back to proxy presentation while the newly focused node becomes the active live overlay.
- Proxy-preview smoke: after a live viewer is demoted back to proxy, verify the node still shows its proxy preview image and the session controls remain responsive for reopen or playback actions. Expected result: the proxy surface remains visible and the viewer chrome keeps the same labels and control hit targets as before the refactor.

## Residual Risks
- The viewer behavior is preserved through new support modules rather than smaller in-file helpers, so `P07` still needs to codify guardrails for the new support files if the thin-facade pattern is meant to remain enforced across later viewer work.

## Ready for Integration
- Yes: the packet-capped viewer entrypoints are now isolated behind viewer-only support files, the exact packet verification and review-gate commands pass, and the public service, bridge, and surface files are all below the P06 size caps.
