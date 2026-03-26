# ARCHITECTURE_REFACTOR Status Ledger

- Updated: `2026-03-25`
- Published packet window: `P00` through `P13`
- Execution note: every non-bootstrap packet runs sequentially in its own wave; later waves stay blocked until the current wave reaches a terminal result.

| Packet | Branch Label | Status | Commit SHA | Commands | Tests | Artifacts | Residual Risks |
|---|---|---|---|---|---|---|---|
| P00 Bootstrap | `codex/architecture-refactor/p00-bootstrap` | PASS |  | planner: `./venv/Scripts/python.exe - <<'PY' ... ARCHITECTURE_REFACTOR_P00_FILE_GATE_PASS ... PY`; planner review gate: `./venv/Scripts/python.exe - <<'PY' ... ARCHITECTURE_REFACTOR_P00_STATUS_PASS ... PY` | PASS (`ARCHITECTURE_REFACTOR_P00_FILE_GATE_PASS`; `ARCHITECTURE_REFACTOR_P00_STATUS_PASS`) | `.gitignore`, `docs/specs/INDEX.md`, `docs/specs/work_packets/architecture_refactor/*` | Bootstrap docs are present in the planning worktree; if `P00` is replayed on a packet branch, replace the blank accepted SHA with the real bootstrap commit SHA |
| P01 Shell Host Composition | `codex/architecture-refactor/p01-shell-host-composition` | PASS | `25e71ee66ef54a99fad1cb23286b2e6d854f75b3` | worker: `QT_QPA_PLATFORM=offscreen /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_contracts.py --ignore=venv -q`; worker review gate: `QT_QPA_PLATFORM=offscreen /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py --ignore=venv -q` | PASS (`12 passed` on the review gate; full verification command reached `205 passed, 329 subtests passed` before failing with 6 shell-suite regressions) | `ea_node_editor/ui/shell/context_bridges.py`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui/shell/presenters.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `tests/test_main_bootstrap.py`, `docs/specs/work_packets/architecture_refactor/P01_shell_host_composition_WRAPUP.md` | The broader shell verification still fails in passive image/pdf and flow-edge coverage outside the P01 bootstrap seam; keep that baseline issue visible for the next packet wave |
| P02 Workspace Library Surface | `codex/architecture-refactor/p02-workspace-library-surface` | PENDING |  |  |  |  |  |
| P03 Project Session Service | `codex/architecture-refactor/p03-project-session-service` | PENDING |  |  |  |  |  |
| P04 Graph Boundary Adapters | `codex/architecture-refactor/p04-graph-boundary-adapters` | PENDING |  |  |  |  |  |
| P05 Graph Invariant Kernel | `codex/architecture-refactor/p05-graph-invariant-kernel` | PENDING |  |  |  |  |  |
| P06 Persistence Invariant Adoption | `codex/architecture-refactor/p06-persistence-invariant-adoption` | PENDING |  |  |  |  |  |
| P07 Runtime Snapshot Context | `codex/architecture-refactor/p07-runtime-snapshot-context` | PENDING |  |  |  |  |  |
| P08 Worker Protocol Split | `codex/architecture-refactor/p08-worker-protocol-split` | PENDING |  |  |  |  |  |
| P09 DPF Runtime Package | `codex/architecture-refactor/p09-dpf-runtime-package` | PENDING |  |  |  |  |  |
| P10 DPF Node Viewer Split | `codex/architecture-refactor/p10-dpf-node-viewer-split` | PENDING |  |  |  |  |  |
| P11 Shell QML Bridge Retirement | `codex/architecture-refactor/p11-shell-qml-bridge-retirement` | PENDING |  |  |  |  |  |
| P12 Graph Canvas Scene Decomposition | `codex/architecture-refactor/p12-graph-canvas-scene-decomposition` | PENDING |  |  |  |  |  |
| P13 Docs Release Traceability | `codex/architecture-refactor/p13-docs-release-traceability` | PENDING |  |  |  |  |  |
