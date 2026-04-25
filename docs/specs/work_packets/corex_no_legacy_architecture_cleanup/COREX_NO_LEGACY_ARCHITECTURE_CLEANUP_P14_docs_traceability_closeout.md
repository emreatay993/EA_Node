# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P14: Docs Traceability Closeout

## Objective

- Publish the no-legacy architecture closeout across canonical docs, requirements, traceability, verification catalogs, and QA evidence.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only docs/verification files needed for this packet

## Preconditions

- `P13` is marked `PASS`.
- All code cleanup packets have produced accepted wrap-up artifacts.

## Execution Dependencies

- `P13`

## Target Subsystems

- `ARCHITECTURE.md`
- `README.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md`
- `scripts/verification_manifest.py`
- `scripts/check_traceability.py`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_dead_code_hygiene.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P14_docs_traceability_closeout_WRAPUP.md`

## Conservative Write Scope

- `ARCHITECTURE.md`
- `README.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md`
- `scripts/verification_manifest.py`
- `scripts/check_traceability.py`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_dead_code_hygiene.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P14_docs_traceability_closeout_WRAPUP.md`

## Required Behavior

- Rewrite architecture and README residual-seam sections so they describe focused bridges, explicit source contracts, current-schema persistence, descriptor-only plugins/add-ons, snapshot-only runtime payloads, typed viewer transport, and canonical launch/import paths.
- Update requirements and traceability rows that previously required old migration hooks, legacy category display compatibility, plugin constructor fallback, missing-plugin placeholder preservation, or compatibility export rows.
- Publish `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md` with packet-by-packet accepted commits, verification commands, residual risks, and manual smoke guidance.
- Register the QA matrix in `docs/specs/INDEX.md` after it exists.
- Update `scripts/verification_manifest.py`, `scripts/check_traceability.py`, and mirrored tests so traceability is semantic-first and points at this packet family rather than older compatibility-closeout families as the active baseline.
- Extend dead-code hygiene for retired compatibility names and paths removed by this packet set.
- Preserve historical packet matrices as archive references only when still useful; do not let historical matrices describe active current architecture.

## Non-Goals

- No further production code changes unless required to repair docs/test drift inside this packet scope.
- No new feature development.
- No broad verification mode expansion beyond packet-owned docs and traceability proof.

## Verification Commands

1. `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_dead_code_hygiene.py --ignore=venv -q`
2. `.\venv\Scripts\python.exe scripts/check_traceability.py`
3. `.\venv\Scripts\python.exe scripts/check_markdown_links.py`

## Review Gate

- `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P14_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/perf/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md`

## Acceptance Criteria

- Canonical docs no longer present legacy compatibility layers as active architecture.
- Traceability and verification catalogs name this packet family as the no-legacy closeout proof.
- Markdown links, traceability checks, and dead-code hygiene pass.

## Handoff Notes

- This packet closes the no-legacy architecture cleanup program.
