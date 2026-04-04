## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/architecture-residual-refactor/p04-viewer-projection-authority-split`
- Commit Owner: `worker`
- Commit SHA: `6767099db5b6108b00289d01f51dce1ca49704cb`
- Changed Files: `docs/specs/work_packets/architecture_residual_refactor/P04_viewer_projection_authority_split_WRAPUP.md`, `ea_node_editor/execution/viewer_session_service.py`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`, `ea_node_editor/ui_qml/viewer_host_service.py`, `ea_node_editor/ui_qml/viewer_session_bridge.py`, `ea_node_editor/ui_qml/viewer_widget_binder.py`, `tests/test_execution_viewer_service.py`, `tests/test_viewer_host_service.py`, `tests/test_viewer_session_bridge.py`, `tests/test_viewer_surface_host.py`
- Artifacts Produced: `docs/specs/work_packets/architecture_residual_refactor/P04_viewer_projection_authority_split_WRAPUP.md`, `ea_node_editor/execution/viewer_session_service.py`, `ea_node_editor/ui_qml/viewer_session_bridge.py`, `ea_node_editor/ui_qml/viewer_host_service.py`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`, `ea_node_editor/ui_qml/viewer_widget_binder.py`, `tests/test_execution_viewer_service.py`, `tests/test_viewer_session_bridge.py`, `tests/test_viewer_host_service.py`, `tests/test_viewer_surface_host.py`

- Added packet-owned viewer projection helpers in `viewer_session_service.py` so canonical session-model extraction, run-required projection, and projection-safe transport trimming are owned by the execution-side seam instead of being recomputed independently in the UI layer.
- Reworked `ViewerSessionBridge` to apply the shared canonical session model, keep run-required projection on that shared seam, preserve the locally captured proxy camera only for the intended blur/refocus cases, and continue projecting pending UI state without becoming a second source of truth for liveness or transport state.
- Updated `ViewerHostService` and `ViewerWidgetBindRequest` to consume and forward the canonical session model directly, so overlay hosting and binder dispatch operate on the same projection contract that the execution-side service publishes.
- Simplified `GraphViewerSurface.qml` so the viewer surface resolves its session projection through `viewerSessionBridge.session_state(...)` instead of walking the full sessions list in QML, keeping QML on rendering duties rather than bridge-side projection lookup.
- Refreshed the inherited viewer regression anchors to prove summary-embedded session models stay authoritative, binder requests receive the canonical model, and the viewer surface uses the direct bridge session lookup while preserving the existing live/proxy interaction behavior.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_execution_viewer_protocol.py tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_viewer_surface_host.py tests/test_dpf_viewer_widget_binder.py --ignore=venv -q` (`58 passed, 9 subtests passed in 10.71s`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py --ignore=venv -q` (`31 passed in 5.16s`)
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree build from `C:\w\ea_node_ed-p04-viewer` with `.\venv\Scripts\python.exe main.py` in a normal desktop session, and use a project that contains at least one viewer-backed node.

1. Focus-only live handoff smoke
Action: open a viewer node so its live overlay appears, then select a different viewer-capable node or clear viewer focus so the original session demotes to proxy mode.
Expected result: the live overlay demotes without an error, the proxy surface keeps a usable preview, and the session status stays consistent with the active viewer focus instead of showing conflicting live/proxy state.

2. Proxy-to-live restore smoke
Action: after the viewer is in proxy mode, refocus the same node so the live overlay is restored.
Expected result: the overlay returns for the focused node, the camera state is preserved across the blur/refocus cycle, and the viewer surface status or badge updates cleanly between `Proxy` and `Live`.

Automated verification remains the primary proof for this packet because the user-visible workflow is intentionally unchanged and the main change is the authority split behind the existing viewer contract.

## Residual Risks

- `ViewerSessionBridge` still owns packet-local pending request projection for open, close, and live-mode transition UX, so later packets can shrink that transient UI projection layer further if the worker protocol ever exposes richer in-flight state directly.
- `ViewerHostService` now consumes the canonical session model, but existing binders still primarily use the flattened request fields; future binder work can retire more of that duplication once packet-external binder consumers move onto the shared projection payload directly.

## Ready for Integration

- Yes: the execution-side viewer projection seam is now shared across the bridge and host layers, the inherited viewer-service, bridge, host, and QML regression anchors all pass, and both the full verification command and review gate passed on the packet branch.
