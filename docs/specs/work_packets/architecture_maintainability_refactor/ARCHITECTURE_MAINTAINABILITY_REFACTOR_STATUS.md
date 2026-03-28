# ARCHITECTURE_MAINTAINABILITY_REFACTOR Status Ledger

- Updated: `2026-03-28`
- Published packet window: `P00` through `P13`
- Execution note: every non-bootstrap packet runs sequentially in its own wave; later waves stay blocked until the current wave reaches a terminal result.

| Packet | Branch Label | Status | Commit SHA | Commands | Tests | Artifacts | Residual Risks |
|---|---|---|---|---|---|---|---|
| P00 Bootstrap | `codex/architecture-maintainability-refactor/p00-bootstrap` | PASS | cd7b43df4f24cd17754d91d4ee7ce3347d510d98 | planner: `./venv/Scripts/python.exe - <<'PY' ... ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_FILE_GATE_PASS ... PY`; planner review gate: `./venv/Scripts/python.exe - <<'PY' ... ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_STATUS_PASS ... PY` | PASS (`ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_FILE_GATE_PASS`; `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_STATUS_PASS`) | `.gitignore`, `docs/specs/INDEX.md`, `docs/specs/work_packets/architecture_maintainability_refactor/*` | Bootstrap docs are materialized on the executor integration base; later packet waves still await acceptance and merge |
| P01 Graph Canvas Compat Retirement | `codex/architecture-maintainability-refactor/p01-graph-canvas-compat-retirement` | PASS | f1ddb5e3d5572a12f7e54e1a1de11caa9b14af3e | worker: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_surface_input_contract.py tests/test_track_h_perf_harness.py tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`; executor review gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/main_window_shell/bridge_contracts.py --ignore=venv -q`; executor validator: `validate_packet_result.py` | PASS (`worker full verification command passed`; `35 passed, 7 subtests passed in 1.45s` on the executor review gate; `VALIDATION PASS` on the executor validator) | `ea_node_editor/ui_qml/graph_canvas_bridge.py`, `tests/main_window_shell/bridge_contracts.py`, `tests/test_main_window_shell.py`, `docs/specs/work_packets/architecture_maintainability_refactor/P01_graph_canvas_compat_retirement_WRAPUP.md` | `GraphCanvasBridge` remains as a documented edge adapter for out-of-scope callers, and a desktop-session manual check is still recommended because automated verification ran with `QT_QPA_PLATFORM=offscreen` |
| P02 Bridge Source Contract Hardening | `codex/architecture-maintainability-refactor/p02-bridge-source-contract-hardening` | PENDING |  |  |  |  |  |
| P03 Shell Host API Retirement | `codex/architecture-maintainability-refactor/p03-shell-host-api-retirement` | PENDING |  |  |  |  |  |
| P04 Project Session Authority Collapse | `codex/architecture-maintainability-refactor/p04-project-session-authority-collapse` | PENDING |  |  |  |  |  |
| P05 Session Envelope Metadata Cleanup | `codex/architecture-maintainability-refactor/p05-session-envelope-metadata-cleanup` | PENDING |  |  |  |  |  |
| P06 Graph Persistence Boundary Cleanup | `codex/architecture-maintainability-refactor/p06-graph-persistence-boundary-cleanup` | PENDING |  |  |  |  |  |
| P07 Graph Mutation Ops Split | `codex/architecture-maintainability-refactor/p07-graph-mutation-ops-split` | PENDING |  |  |  |  |  |
| P08 Node SDK Surface Cleanup | `codex/architecture-maintainability-refactor/p08-node-sdk-surface-cleanup` | PENDING |  |  |  |  |  |
| P09 Runtime Protocol Compat Removal | `codex/architecture-maintainability-refactor/p09-runtime-protocol-compat-removal` | PENDING |  |  |  |  |  |
| P10 Viewer Session Backend Split | `codex/architecture-maintainability-refactor/p10-viewer-session-backend-split` | PENDING |  |  |  |  |  |
| P11 Graph Canvas Scene Decomposition | `codex/architecture-maintainability-refactor/p11-graph-canvas-scene-decomposition` | PENDING |  |  |  |  |  |
| P12 Geometry Theme Perf Cleanup | `codex/architecture-maintainability-refactor/p12-geometry-theme-perf-cleanup` | PENDING |  |  |  |  |  |
| P13 Verification Docs Traceability Closeout | `codex/architecture-maintainability-refactor/p13-verification-docs-traceability-closeout` | PENDING |  |  |  |  |  |
