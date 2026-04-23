# COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION P00: Bootstrap

## Packet Metadata

- Packet: `P00`
- Title: `Bootstrap`
- Execution Dependencies: `none`
- Owner: orchestrator
- Status: `PASS`

## Objective

- Materialize this subagent-ready packet set from `PLANS_TO_IMPLEMENT/in_progress/COREX Architecture Entry Point Reduction Plan.md`.
- Register the packet set in `docs/specs/INDEX.md`.
- Mark `P00` as `PASS` and leave `P01` through `P05` as `PENDING`.

## Preconditions

- The architecture audit plan exists in `PLANS_TO_IMPLEMENT/in_progress/COREX Architecture Entry Point Reduction Plan.md`.
- The target merge branch for later execution is `main`.

## Execution Dependencies

- none

## Target Subsystems

- `PLANS_TO_IMPLEMENT/in_progress/COREX Architecture Entry Point Reduction Plan.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/`

## Conservative Write Scope

- `PLANS_TO_IMPLEMENT/in_progress/COREX Architecture Entry Point Reduction Plan.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/*`

## Required Behavior

- Create the manifest, status ledger, packet specs, and standalone prompts.
- Include explicit execution waves in the manifest.
- Use branch labels in the `codex/corex-architecture-entry-point-reduction/pXX-<slug>` style.
- Make every implementation packet include `Model / Context Hint`, `Execution Dependencies`, `Conservative Write Scope`, `Verification Commands`, `Review Gate`, `Expected Artifacts`, and a packet wrap-up artifact.
- Ensure each implementation packet's wrap-up path appears in both `Expected Artifacts` and `Conservative Write Scope`.

## Non-Goals

- Do not implement `P01` or later packets in the bootstrap thread.
- Do not create packet worktrees.
- Do not run implementation verification.

## Verification Commands

1. Planner file gate: `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P00_FILE_GATE_PASS`
2. Planner status gate: `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P00_STATUS_PASS`

## Review Gate

`COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P00_STATUS_PASS`

## Expected Artifacts

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_MANIFEST.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_STATUS.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P00_bootstrap.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P01_action_inventory_guardrails.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P01_action_inventory_guardrails_PROMPT.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P02_canonical_controller_and_bridge.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P02_canonical_controller_and_bridge_PROMPT.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P03_pyqt_action_route_merge.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P03_pyqt_action_route_merge_PROMPT.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P04_qml_action_route_merge.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P04_qml_action_route_merge_PROMPT.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P05_closeout_docs_and_metrics.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_P05_closeout_docs_and_metrics_PROMPT.md`
- `docs/specs/INDEX.md`
- `PLANS_TO_IMPLEMENT/in_progress/COREX Architecture Entry Point Reduction Plan.md`

## Acceptance Criteria

- Packet docs exist on disk.
- The manifest has sequential `Execution Waves` for `P01` through `P05`.
- The status ledger marks `P00` as `PASS` and every implementation packet as `PENDING`.
- `docs/specs/INDEX.md` links the manifest and status ledger.

## Handoff Notes

- The executor must treat the saved packet docs as the only source of truth.
- Later packet workers should not rely on the planning-chat transcript.
