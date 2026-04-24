# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P00: Bootstrap

## Objective

Publish the clean architecture restructure packet set and hand later implementation packets to fresh top-level executor threads.

## Preconditions

- `PLANS_TO_IMPLEMENT/in_progress/COREX Clean Architecture Restructure.md` exists.
- The completed `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP` packet family remains the no-legacy baseline.

## Target Subsystems

- `docs/specs/work_packets/corex_clean_architecture_restructure/`
- `docs/specs/INDEX.md`

## Conservative Write Scope

- `docs/specs/work_packets/corex_clean_architecture_restructure/**`
- `docs/specs/INDEX.md`

## Required Behavior

- Create the manifest, status ledger, packet specs, and standalone prompts.
- Mark `P00` as `PASS`.
- Leave `P01` through `P12` as `PENDING`.
- Register the manifest and status ledger in `docs/specs/INDEX.md`.
- Stop after bootstrap; do not implement later packets in the planning thread.

## Non-Goals

- No production code changes.
- No verification-runner changes.
- No packet implementation.

## Verification Commands

- Manual inspection of created packet artifacts.

## Review Gate

none

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_MANIFEST.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_STATUS.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_P00_bootstrap.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_P01_runtime_contracts.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_P12_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria

- Packet docs exist.
- `P00` is `PASS`; implementation packets are `PENDING`.
- Fresh-thread executor prompts can use the packet set without relying on the planning conversation.

## Handoff Notes

Use `$subagent-work-packet-executor` in fresh top-level threads. Do not spawn an executor subagent from this planning thread.
