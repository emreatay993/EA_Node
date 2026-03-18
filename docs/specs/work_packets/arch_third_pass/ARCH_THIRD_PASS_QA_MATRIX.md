# ARCH_THIRD_PASS QA Matrix

- Updated: `2026-03-18`
- Packet set: `ARCH_THIRD_PASS` (`P01` through `P08`)
- Scope: closeout regression slice and traceability evidence for the targeted architecture follow-up packets after `ARCH_SECOND_PASS`.

## Accepted Packet Outcomes

| Packet | Accepted Commit | Outcome | Primary Evidence |
|---|---|---|---|
| `P01` | `6d12628be9e8003de154a16e14b7aa2e5270b84d` | Kept `ShellWindow` as a thinner composition root and preserved bootstrap/test seams. | `docs/specs/work_packets/arch_third_pass/P01_shell_composition_root_WRAPUP.md` |
| `P02` | `efa6352b3467ca462c62382ccbe46f24fb79f509` | Split workspace-library behavior into packet-owned capability seams without changing shell workflows. | `docs/specs/work_packets/arch_third_pass/P02_workspace_library_capabilities_WRAPUP.md` |
| `P03` | `d17d381c260ded6d5061f3d8adab9163c5746aa0` | Moved packet-owned shell/canvas roots onto focused bridges before raw compatibility fallbacks. | `docs/specs/work_packets/arch_third_pass/P03_bridge_first_shell_canvas_WRAPUP.md` |
| `P04` | `dd7d89fe610ce41d28ac19910b08f3348790fa57` | Introduced explicit scene context/services behind the stable `GraphSceneBridge` surface. | `docs/specs/work_packets/arch_third_pass/P04_scene_mutation_contracts_WRAPUP.md` |
| `P05` | `00f72cc38962760b63b92c1ce681f83614514f33` | Removed packet-owned passive-media reliance on raw shell/scene globals. | `docs/specs/work_packets/arch_third_pass/P05_passive_media_bridge_cleanup_WRAPUP.md` |
| `P06` | `7767de2d5e50d750735dcd087c6c0f0a0a84226c` | Made worker runtime seams explicit and locked the `REQ-NODE-011` data-dependency behavior. | `docs/specs/work_packets/arch_third_pass/P06_execution_worker_runtime_WRAPUP.md` |
| `P07` | `5c7a69baeaf6c1823473fde995d910e5498e90d1` | Centralized registry-backed validation/normalization across model, persistence, and compiler seams without changing persisted shape. | `docs/specs/work_packets/arch_third_pass/P07_validation_persistence_centralization_WRAPUP.md` |
| `P08` | `see wrap-up` | Publishes the packet-set QA matrix, architecture closure summary, and final verification traceability evidence. | `docs/specs/work_packets/arch_third_pass/P08_verification_traceability_WRAPUP.md`, this matrix |

## Closure Regression Slice

| Coverage | Command | Why This Closes The Packet Set | Packet Anchors |
|---|---|---|---|
| Proof audit / review gate | `./venv/Scripts/python.exe scripts/check_traceability.py` | Confirms the packet-owned verification docs and requirement-facing proof layer stay aligned after the closeout edits. | `P08`, `REQ-QA-014`, `REQ-QA-017`, `REQ-QA-018` |
| Verification workflow audit | `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run` | Revalidates the documented developer entry point and its current fast-slice command composition without reopening broader verification scope. | `P08`, `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` |
| Shell/canvas/passive/execution/persistence slice | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_passive_graph_surface_host tests.test_execution_client tests.test_execution_worker tests.test_serializer_schema_migration -v` | Covers the cross-packet seams most likely to regress together: shell/bootstrap/QML bridge ownership, `GraphCanvas` passive-media host routing, execution client/worker runtime, and serializer-migration normalization. | `P01` through `P07`, `REQ-ARCH-002`, `REQ-ARCH-010`, `REQ-ARCH-011`, `REQ-NODE-011` |

## 2026-03-18 Closure Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Project-venv review gate passed after the P08 closeout docs were refreshed. |
| `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run` | PASS | Dry-run output enumerated the current fast verification slice as `pytest -n auto -m 'not gui and not slow'` with the four documented shell-wrapper `--ignore=` exclusions. |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_passive_graph_surface_host tests.test_execution_client tests.test_execution_worker tests.test_serializer_schema_migration -v` | PASS | Focused closeout regression slice passed in the project venv: `172` tests in `233.536s` across the shell/canvas, passive-media, execution, and serializer-migration seams. |

## Traceability Anchors

| Requirement Anchor | Closeout Evidence |
|---|---|
| `REQ-ARCH-002`, `REQ-ARCH-010`, `REQ-ARCH-011` | `ARCHITECTURE.md` closure snapshot plus the focused shell/canvas regression slice centered on `tests.test_main_window_shell` and `tests.test_passive_graph_surface_host`. |
| `REQ-NODE-011`, `AC-REQ-NODE-011-01` | `tests.test_execution_worker`, `tests.test_execution_client`, and the accepted `P06_execution_worker_runtime_WRAPUP.md` outcome. |
| `REQ-QA-014` | Existing published workflow in `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` plus the P08 `--mode fast --dry-run` audit. |
| `REQ-QA-017`, `REQ-QA-018` | `scripts/check_traceability.py` and the already-approved proof docs under `docs/specs/perf/`. |

## Residual Risks

- Raw compatibility context properties still exist for non-packet-owned QML consumers and remaining shell-side helpers.
- `workspace_library_controller.py` and packet-external fragment-validation code still rely on internal seams that were intentionally left in place to keep this packet validator-compatible.
- Unknown-plugin graphs still preserve the preexisting compiler fallback when one side of an edge cannot be resolved.
- Fresh-process execution remains the required harness contract for some shell-backed tests because the Windows Qt/QML multi-`ShellWindow()` lifetime issue is not fully resolved.
