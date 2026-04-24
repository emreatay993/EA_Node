# P01 No-Legacy Guardrails Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/corex-no-legacy-architecture-cleanup/p01-no-legacy-guardrails`
- Commit Owner: `worker`
- Commit SHA: `c413beae3eab13eb40aaceb86bd143587900d6de`
- Changed Files: `scripts/verification_manifest.py`, `tests/main_window_shell/bridge_contracts_graph_canvas.py`, `tests/main_window_shell/bridge_qml_boundaries.py`, `tests/test_architecture_boundaries.py`, `tests/test_dead_code_hygiene.py`, `tests/test_graph_action_contracts.py`, `tests/test_main_window_shell.py`, `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P01_no_legacy_guardrails_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P01_no_legacy_guardrails_WRAPUP.md`, `scripts/verification_manifest.py`

Added `COREX_NO_LEGACY_GUARDRAIL_INVENTORY` for later-packet compatibility cleanup surfaces. Ownership is: P02 for `GraphCanvasBridge` and canvas QML compatibility aliases, P03 for ShellWindow graph-action route alias anchors, P06 for old project and preference schema compatibility paths, P10 for legacy plugin class probing, P11 for runtime `project_doc` and `project_path` rebuild paths, and P13 for telemetry/import shims.

Updated packet-owned tests so the current post-P05 baseline is `GraphActionController`, `GraphActionBridge`, and split graph-canvas state/command bridges. Remaining legacy wrapper assertions are marked as P02 pre-cleanup anchors instead of implying legacy bridge parity is the desired end state.

## Verification

- FAIL: `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py tests/test_architecture_boundaries.py --ignore=venv -q` (initial stale payload-builder helper assertion; remediated)
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py tests/test_architecture_boundaries.py --ignore=venv -q`
- FAIL: `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py tests/test_architecture_boundaries.py tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q` (initial inherited legacy graph-canvas action slot assertions; remediated)
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py tests/test_architecture_boundaries.py tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

This packet is internal guardrail/test preparation only. No desktop workflow changed; the meaningful manual check is to inspect the guardrail inventory and confirm each category maps to the intended later packet before starting P02 or later cleanup work.

## Residual Risks

Later packets must update or retire the P01 guardrail anchors when they delete their owned compatibility surfaces. The full verification run emitted third-party Ansys DPF deprecation warnings, but no packet-owned test failures remain.

## Ready for Integration

- Yes: P01 stayed inside packet scope, committed the substantive guardrail changes, produced the wrap-up artifact, and both required verification commands pass.
