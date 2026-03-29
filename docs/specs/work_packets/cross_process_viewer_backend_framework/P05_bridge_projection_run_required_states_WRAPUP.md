# P05 Bridge Projection Run-Required States Wrap-Up

## Implementation Summary
- Packet: P05
- Branch Label: codex/cross-process-viewer-backend-framework/p05-bridge-projection-run-required-states
- Commit Owner: worker
- Commit SHA: 75152ac7290d14b55aa2753e1c9a39bacbab86ed
- Changed Files: ea_node_editor/ui/shell/controllers/project_session_services.py, ea_node_editor/ui/shell/controllers/run_controller.py, ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml, ea_node_editor/ui_qml/viewer_session_bridge.py, tests/test_project_session_controller_unit.py, tests/test_shell_project_session_controller.py, tests/test_shell_run_controller.py, tests/test_viewer_session_bridge.py, tests/test_viewer_surface_contract.py, tests/test_viewer_surface_host.py, docs/specs/work_packets/cross_process_viewer_backend_framework/P05_bridge_projection_run_required_states_WRAPUP.md
- Artifacts Produced: ea_node_editor/ui/shell/controllers/project_session_services.py, ea_node_editor/ui/shell/controllers/run_controller.py, ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml, ea_node_editor/ui_qml/viewer_session_bridge.py, tests/test_project_session_controller_unit.py, tests/test_shell_project_session_controller.py, tests/test_shell_run_controller.py, tests/test_viewer_session_bridge.py, tests/test_viewer_surface_contract.py, tests/test_viewer_surface_host.py, docs/specs/work_packets/cross_process_viewer_backend_framework/P05_bridge_projection_run_required_states_WRAPUP.md

This packet reduces the viewer session bridge to authoritative projection plus intent forwarding, seeds saved-project reopen and reset flows with run-required viewer projection state, and updates the viewer surface so blocked live-open states present explicit rerun-required messaging instead of a blank live pane. Project open, restore, rerun, and worker-reset paths now clear live transport safely while preserving projection-safe summary, backend, revision, camera, and blocker metadata for the shell-facing viewer contract.

## Verification
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_shell_run_controller.py tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_surface_contract.py tests/test_viewer_surface_host.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives
1. Open a project with a DPF viewer node that was previously run and confirm the viewer surface shows a blocked rerun-required state instead of a blank live widget after restore.
2. Rerun the affected workspace and confirm the rerun-required state clears and the live viewer can bind again without leaving a stale native widget behind.

## Residual Risks
- Automated coverage runs under `QT_QPA_PLATFORM=offscreen`; a native desktop session is still the best proof for saved-project reopen, rerun-required messaging, and post-rerun widget rebinding against a real DPF transport bundle.

## Ready for Integration
- Yes: authoritative run-required projection, blocker messaging, and viewer-surface contract updates are in place, and both packet verification commands plus the review gate passed.
