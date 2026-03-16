# GRAPH_SURFACE_INPUT Status Ledger

- Updated: `2026-03-16`
- Environment note: packet set bootstrapped; implementation progress tracked per packet.

| Packet | Branch Label | Status | Commit SHA | Commands | Tests | Artifacts | Residual Risks |
|---|---|---|---|---|---|---|---|
| P00 Bootstrap | `codex/graph-surface-input/p00-bootstrap` | PASS | `n/a` | create `docs/specs/work_packets/graph_surface_input/*`; add narrow `.gitignore` exception so the new packet docs are trackable; add manifest, status ledger, and packet contract/prompt files for `P00` through `P09`; update `docs/specs/INDEX.md`; run `GRAPH_SURFACE_INPUT_P00_FILE_GATE_PASS` verification command from `GRAPH_SURFACE_INPUT_P00_bootstrap.md` | PASS (`1/1`): file/index gate returned `GRAPH_SURFACE_INPUT_P00_FILE_GATE_PASS` | `.gitignore`, `docs/specs/work_packets/graph_surface_input/*`, `docs/specs/INDEX.md` | none |
| P01 Host Drag Layer Foundation | `codex/graph-surface-input/p01-host-drag-layer-foundation` | PENDING | `n/a` | pending | pending | pending | host drag/select regressions not yet covered |
| P02 Surface Input Contract | `codex/graph-surface-input/p02-surface-input-contract` | PENDING | `n/a` | pending | pending | pending | embedded-control ownership contract not yet implemented |
| P03 Interaction Bridge | `codex/graph-surface-input/p03-interaction-bridge` | PENDING | `n/a` | pending | pending | pending | inline commits still depend on selected-node routing |
| P04 Shared Surface Controls | `codex/graph-surface-input/p04-shared-surface-controls` | PENDING | `n/a` | pending | pending | pending | graph-surface controls still duplicated/ad hoc |
| P05 Inline Core Editors | `codex/graph-surface-input/p05-inline-core-editors` | PENDING | `n/a` | pending | pending | pending | standard inline editors still sit behind host overlay risk |
| P06 Inline Extended Editors | `codex/graph-surface-input/p06-inline-extended-editors` | PENDING | `n/a` | pending | pending | pending | graph-surface `textarea` / `path` inline editing remains unsupported |
| P07 Media Surface Migration | `codex/graph-surface-input/p07-media-surface-migration` | PENDING | `n/a` | pending | pending | pending | media crop button still depends on hover proxy compatibility layer |
| P08 Pointer Regression Audit | `codex/graph-surface-input/p08-pointer-regression-audit` | PENDING | `n/a` | pending | pending | pending | future interactive surfaces can still regress without locked audits |
| P09 Docs Traceability | `codex/graph-surface-input/p09-docs-traceability` | PENDING | `n/a` | pending | pending | pending | TODO/docs/QA traceability remains open until final packet |
