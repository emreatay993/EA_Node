## Implementation Summary
- Packet: `P06`
- Branch Label: `codex/ui-context-scalability-refactor/p06-viewer-surface-isolation`
- Commit Owner: `worker`
- Commit SHA: `3769e0fc9eea2392a7756c874fb6fafd6a5d802c`
- Changed Files: `docs/specs/work_packets/ui_context_scalability_refactor/P06_viewer_surface_isolation_WRAPUP.md`, `ea_node_editor/execution/viewer_session_service.py`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`, `ea_node_editor/ui_qml/viewer_session_bridge.py`, `tests/test_execution_viewer_service.py`, `tests/test_viewer_session_bridge.py`, `tests/test_viewer_surface_contract.py`
- Artifacts Produced: `docs/specs/work_packets/ui_context_scalability_refactor/P06_viewer_surface_isolation_WRAPUP.md`, `ea_node_editor/execution/viewer_session_service.py`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`, `ea_node_editor/ui_qml/viewer_session_bridge.py`, `tests/test_execution_viewer_service.py`, `tests/test_viewer_session_bridge.py`, `tests/test_viewer_surface_contract.py`

Kept the packet fully inside the documented write scope by folding the viewer service, bridge, and surface implementations back into the three P06-owned entry files. `viewer_session_service.py` and `viewer_session_bridge.py` now carry their implementation payloads directly while staying under the packet line caps, and `GraphViewerSurface.qml` now hosts the viewer surface implementation through an in-file dynamic viewer object instead of a separate helper file.

Updated the packet-owned regression anchors so P06 now enforces both the line-budget caps and the scope boundary: the tests assert the thin in-scope entry files remain capped and that the previously introduced out-of-scope support files are absent from the accepted branch state.

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
- The remediated scoped implementation relies on compact embedded payloads inside the three capped entry files to satisfy the packet scope and line-budget requirements simultaneously, so later maintenance work should treat those files carefully until `P07` adds machine-enforced guardrails for future viewer refactors.

## Ready for Integration
- Yes: the accepted diff is back inside the P06 conservative write scope, the exact packet verification and review-gate commands pass, and the public service, bridge, and surface files are all below the P06 size caps.
