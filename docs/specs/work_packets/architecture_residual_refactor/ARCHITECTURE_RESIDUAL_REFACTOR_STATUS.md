# ARCHITECTURE_RESIDUAL_REFACTOR Status Ledger

- Updated: `2026-04-03`
- Published packet window: `P00` through `P08`
- Execution note: every non-bootstrap packet runs sequentially in its own wave; later waves stay blocked until the current wave reaches a terminal result.

| Packet | Branch Label | Status | Commit SHA | Commands | Tests | Artifacts | Residual Risks |
|---|---|---|---|---|---|---|---|
| P00 Bootstrap | `codex/architecture-residual-refactor/p00-bootstrap` | PASS | 0b63f03f5fd887c6f1c4a191ca4c86bb3425fc4d | planner: `ARCHITECTURE_RESIDUAL_REFACTOR_P00_FILE_GATE_PASS`; planner review gate: `ARCHITECTURE_RESIDUAL_REFACTOR_P00_STATUS_PASS` | PASS (`ARCHITECTURE_RESIDUAL_REFACTOR_P00_FILE_GATE_PASS`; `ARCHITECTURE_RESIDUAL_REFACTOR_P00_STATUS_PASS`) | `docs/ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md`, `docs/specs/INDEX.md`, `.gitignore`, `docs/specs/work_packets/architecture_residual_refactor/*` | Bootstrap docs are established on disk; later packets remain pending and unexecuted until a fresh executor thread starts the sequential packet waves |
| P01 Shell Host Surface Retirement | `codex/architecture-residual-refactor/p01-shell-host-surface-retirement` | FAIL | c6513f0b5cbde243afb58916eaa6f303c03a48e9 | worker verify: `tests/test_main_bootstrap.py tests/test_project_session_controller_unit.py tests/test_workspace_library_controller_unit.py tests/test_shell_project_session_controller.py tests/test_shell_run_controller.py tests/test_main_window_shell.py` FAIL; executor review gate: `tests/test_main_bootstrap.py tests/test_project_session_controller_unit.py tests/test_workspace_library_controller_unit.py` PASS; executor validator: `VALIDATION FAIL (Final Verification Verdict must be PASS before acceptance)` | PASS (`tests/test_main_bootstrap.py`; `tests/test_project_session_controller_unit.py`; `tests/test_workspace_library_controller_unit.py`); FAIL (`tests/test_main_window_shell.py::MainWindowShellPassivePdfNodesTests::test_class_runs_in_subprocess`) | `docs/specs/work_packets/architecture_residual_refactor/P01_shell_host_surface_retirement_WRAPUP.md` | Required packet verification remains blocked by the inherited passive-PDF regression in `ea_node_editor/ui_qml/graph_scene_payload_builder.py`; Wave 2+ stay blocked until the user chooses how to handle this out-of-scope failure |
| P02 Shell Lifecycle Isolation Hardening | `codex/architecture-residual-refactor/p02-shell-lifecycle-isolation-hardening` | PENDING |  |  |  |  |  |
| P03 Graph Scene Bridge Decomposition | `codex/architecture-residual-refactor/p03-graph-scene-bridge-decomposition` | PENDING |  |  |  |  |  |
| P04 Viewer Projection Authority Split | `codex/architecture-residual-refactor/p04-viewer-projection-authority-split` | PENDING |  |  |  |  |  |
| P05 Runtime Snapshot Boundary Decoupling | `codex/architecture-residual-refactor/p05-runtime-snapshot-boundary-decoupling` | PENDING |  |  |  |  |  |
| P06 Graph Mutation Service Decoupling | `codex/architecture-residual-refactor/p06-graph-mutation-service-decoupling` | PENDING |  |  |  |  |  |
| P07 Shared Runtime Contract Extraction | `codex/architecture-residual-refactor/p07-shared-runtime-contract-extraction` | PENDING |  |  |  |  |  |
| P08 Verification Architecture Closeout | `codex/architecture-residual-refactor/p08-verification-architecture-closeout` | PENDING |  |  |  |  |  |
