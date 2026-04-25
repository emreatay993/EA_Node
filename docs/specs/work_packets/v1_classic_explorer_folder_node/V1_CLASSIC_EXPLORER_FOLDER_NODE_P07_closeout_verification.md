# V1_CLASSIC_EXPLORER_FOLDER_NODE P07: Closeout Verification

## Objective
- Publish final QA evidence for the V1 Classic Explorer folder node, update durable specs/traceability where required, run final packet-level proof commands, and close the packet set without changing runtime behavior.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only docs/proof files needed for closeout

## Preconditions
- `P01` through `P06` are marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- No later `V1_CLASSIC_EXPLORER_FOLDER_NODE` packet exists.

## Execution Dependencies
- `P01`
- `P02`
- `P03`
- `P04`
- `P05`
- `P06`

## Target Subsystems
- `docs/specs/perf/V1_CLASSIC_EXPLORER_FOLDER_NODE_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`

## Conservative Write Scope
- `docs/specs/perf/V1_CLASSIC_EXPLORER_FOLDER_NODE_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P07_closeout_verification_WRAPUP.md`

## Source Public Entry Points
- Durable spec docs and packet QA matrix only.

## Regression Public Entry Points
- Traceability checker, markdown link checker, context budget checker, and fast verification runner.

## State Owner
- Closeout docs own retained evidence and requirement references.
- Runtime/source behavior remains owned by earlier packets.

## Allowed Dependencies
- Existing docs/proof scripts and packet status ledger.
- Wrap-up artifacts from `P01` through `P06`.

## Required Behavior
- Create `docs/specs/perf/V1_CLASSIC_EXPLORER_FOLDER_NODE_QA_MATRIX.md`.
- Update requirement, traceability, and index docs only where needed to retain durable evidence for the implemented feature.
- Run and record final verification/proof commands.
- Leave product source and tests unchanged.

## Required Invariants
- Publish a QA matrix with packet-by-packet evidence, commands, manual test directives, and residual risks.
- Update requirement/traceability docs only where the implemented feature creates durable requirement coverage.
- Keep links valid from `docs/specs/INDEX.md`.
- Do not alter product source or tests in this packet.

## Non-Goals
- No feature implementation.
- No test behavior changes.
- No packet branch cleanup or merge execution.

## Forbidden Shortcuts
- Do not mark unverified packet evidence as passed.
- Do not remove packet residual risks from the ledger without supporting proof.
- Do not broaden verification to destructive or shell-isolation phases unless earlier packet evidence shows a cross-cutting shell risk.

## Required Tests
- Run the final docs/proof checks listed below.
- Run the fast verification command after all implementation packets are integrated.

## Verification Anchor Handoff
- This final packet does not hand tests to a later packet.
- If closeout discovers stale earlier assertions, route remediation to the owning packet before marking `P07` as `PASS`.

## Verification Commands
1. `.\venv\Scripts\python.exe scripts\run_verification.py --mode fast`
2. `.\venv\Scripts\python.exe scripts\check_traceability.py`
3. `.\venv\Scripts\python.exe scripts\check_markdown_links.py`
4. `.\venv\Scripts\python.exe scripts\check_context_budgets.py`

## Review Gate
- `.\venv\Scripts\python.exe scripts\check_markdown_links.py`

## Expected Artifacts
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P07_closeout_verification_WRAPUP.md`
- `docs/specs/perf/V1_CLASSIC_EXPLORER_FOLDER_NODE_QA_MATRIX.md`

## Acceptance Criteria
- QA matrix exists and records final packet evidence for `P01` through `P07`.
- Requirement and traceability docs include the V1 Classic Explorer feature only where durable spec updates are required.
- Fast verification and docs/proof checks pass or any failures are documented as terminal residual risks.
- Packet ledger is internally consistent and ready for executor merge-readiness reporting.

## Handoff Notes
- This is the final packet. Do not start additional feature work from this packet branch.
- After `P07` passes, the executor reports accepted packet branches and waits for user-triggered merge.
