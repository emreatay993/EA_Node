# COMMENT_FLOATING_POPOVER Status Ledger

- Updated: `2026-04-24`
- Integration base: `main`
- Published packet window: `P00` through `P03`
- Execution note: use the manifest `Execution Waves` as the authoritative parallelism contract. Later waves remain blocked until every packet in the current wave reaches a terminal result.
- Worker model override: implementation workers for `P01` through `P03` use `gpt-5.5` with `xhigh` reasoning.

| Packet | Branch Label | Status | Commit SHA | Commands | Tests | Artifacts | Residual Risks |
|---|---|---|---|---|---|---|---|
| P00 Bootstrap | `codex/comment-floating-popover/p00-bootstrap` | PASS | `bootstrap-docs-uncommitted` | planner: `COMMENT_FLOATING_POPOVER_P00_FILE_GATE_PASS`; planner review gate: `COMMENT_FLOATING_POPOVER_P00_STATUS_PASS` | PASS (`COMMENT_FLOATING_POPOVER_P00_FILE_GATE_PASS`; `COMMENT_FLOATING_POPOVER_P00_STATUS_PASS`) | `docs/specs/INDEX.md`, `docs/specs/work_packets/comment_floating_popover/*` | Bootstrap docs are local to this checkout until committed or merged; commit them to the target merge branch before executor-created packet worktrees are expected to read them. |
| P01 Overlay Shell | `codex/comment-floating-popover/p01-overlay-shell` | PENDING |  |  |  |  |  |
| P02 Action Wiring and Commit Flow | `codex/comment-floating-popover/p02-action-wiring-and-commit-flow` | PENDING |  |  |  |  |  |
| P03 Tests and Verification | `codex/comment-floating-popover/p03-tests-and-verification` | PENDING |  |  |  |  |  |
