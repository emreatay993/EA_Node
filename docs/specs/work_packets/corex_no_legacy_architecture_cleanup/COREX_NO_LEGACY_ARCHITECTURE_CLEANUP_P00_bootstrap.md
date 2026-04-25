# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P00: Bootstrap

## Objective

- Establish the no-legacy architecture cleanup packet set and register it for fresh-thread executor use.

## Preconditions

- Current branch is `main`.
- `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION` through P05 is present on the planning branch.
- Uncommitted user work remains user-owned and must not be overwritten by packet docs.

## Execution Dependencies

- none

## Target Subsystems

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/`
- `docs/specs/INDEX.md`

## Conservative Write Scope

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/*`
- `docs/specs/INDEX.md`

## Required Behavior

- Create the manifest, status ledger, packet specs, and standalone prompts for `P00` through `P14`.
- Mark `P00` as `PASS` and every implementation packet as `PENDING`.
- Register the manifest and status ledger in `docs/specs/INDEX.md`.
- Stop after bootstrap and hand execution to a fresh top-level executor thread.

## Non-Goals

- No production code changes.
- No test changes.
- No execution of `P01` or later.

## Verification Commands

1. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_FILE_GATE_PASS`
2. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_STATUS_PASS`

## Review Gate

- `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_STATUS_PASS`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_MANIFEST.md`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_bootstrap.md`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P01_no_legacy_guardrails.md`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P14_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria

- Packet docs exist on disk.
- Manifest contains explicit execution waves.
- Status ledger marks only `P00` as `PASS`.
- `docs/specs/INDEX.md` links the manifest and status ledger.

## Handoff Notes

- Start a fresh top-level thread with `$subagent-work-packet-executor`, the packet-set path, and target merge branch `main`.
