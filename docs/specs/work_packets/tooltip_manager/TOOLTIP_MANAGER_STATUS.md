# TOOLTIP_MANAGER Status Ledger

- Updated: `2026-04-13`
- Integration base: `main`
- Published packet window: `P00` through `P03`
- Execution note: use the manifest `Execution Waves` as the authoritative parallelism contract. Later waves remain blocked until every packet in the current wave reaches a terminal result.

| Packet | Branch Label | Status | Commit SHA | Commands | Tests | Artifacts | Residual Risks |
|---|---|---|---|---|---|---|---|
| P00 Bootstrap | `codex/tooltip-manager/p00-bootstrap` | PASS | `67e0335cd2b152f2dffbb803c365afd01df22006` | planner: `TOOLTIP_MANAGER_P00_FILE_GATE_PASS`; planner review gate: `TOOLTIP_MANAGER_P00_STATUS_PASS` | PASS (`TOOLTIP_MANAGER_P00_FILE_GATE_PASS`; `TOOLTIP_MANAGER_P00_STATUS_PASS`) | `docs/specs/INDEX.md`, `docs/specs/work_packets/tooltip_manager/*` | Bootstrap docs are generated in the working tree. Executor-created worktrees need these docs committed or otherwise present on the chosen target merge branch before implementation execution. |
| P01 Tooltip Preference and Manager Contract | `codex/tooltip-manager/p01-tooltip-preference-and-manager-contract` | PENDING | `pending` | pending | pending | `docs/specs/work_packets/tooltip_manager/P01_tooltip_preference_and_manager_contract_WRAPUP.md` | Blocked until execution starts. |
| P02 View Menu and Tooltip Surface Adoption | `codex/tooltip-manager/p02-view-menu-and-tooltip-surface-adoption` | PENDING | `pending` | pending | pending | `docs/specs/work_packets/tooltip_manager/P02_view_menu_and_tooltip_surface_adoption_WRAPUP.md` | Blocked until P01 is PASS. |
| P03 Collision-Avoidance Tooltip Copy | `codex/tooltip-manager/p03-collision-avoidance-tooltip-copy` | PENDING | `pending` | pending | pending | `docs/specs/work_packets/tooltip_manager/P03_collision_avoidance_tooltip_copy_WRAPUP.md` | Blocked until P01 is PASS. |
