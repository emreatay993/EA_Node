# VERIFICATION_SPEED P05: Docs Traceability

## Objective
- Publish the new verification workflow, QA matrix, and traceability updates so the repo stops recommending `unittest discover` as the default day-to-day loop while still preserving the approved isolated shell fallback.

## Preconditions
- `P00` is marked `PASS` in [VERIFICATION_SPEED_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md).
- `P01`, `P02`, `P03`, and `P04` are marked `PASS`.
- No later `VERIFICATION_SPEED` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`
- `P04`

## Target Subsystems
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- a new verification workflow matrix under `docs/specs/perf/`
- `.gitignore` only if a narrow exception is needed for the new matrix doc

## Conservative Write Scope
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md`
- `.gitignore`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md`

## Required Behavior
- Update `README.md` and `docs/GETTING_STARTED.md` so the default developer workflow points to `scripts/run_verification.py` rather than `unittest discover`.
- Keep the focused acceptance-gate commands and shell fallback guidance that are still relevant; do not delete the approved module-level `unittest` coverage where it remains authoritative.
- Add `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` that records:
  - the approved `fast`, `gui`, `slow`, and `full` command shapes
  - the current isolation rules for the four shell-wrapper modules
  - the measured baseline timings from this packet set manifest
  - the current `pytest-xdist` fallback expectation
  - the known serializer baseline failure if it is still unresolved when this packet lands
- Update QA/traceability docs so the new runner and matrix are discoverable from the canonical requirement pack.
- Add a narrow `.gitignore` exception if required so the new QA matrix doc is tracked.
- Keep the packet focused on documentation and traceability. Do not change runner behavior or tests here.

## Non-Goals
- No production code changes.
- No test-body changes.
- No expansion into baseline serializer repair.

## Verification Commands
1. `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run`
2. `git diff --check -- .gitignore README.md docs/GETTING_STARTED.md docs/specs/requirements/90_QA_ACCEPTANCE.md docs/specs/requirements/TRACEABILITY_MATRIX.md docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md`

## Review Gate
- `git diff --check -- .gitignore README.md docs/GETTING_STARTED.md docs/specs/requirements/90_QA_ACCEPTANCE.md docs/specs/requirements/TRACEABILITY_MATRIX.md docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md`

## Expected Artifacts
- `docs/specs/work_packets/verification_speed/P05_docs_traceability_WRAPUP.md`
- `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md`

## Acceptance Criteria
- The dry-run command reflects the final intended verification workflow.
- The repo's default developer-facing test docs no longer recommend `unittest discover` as the primary daily loop.
- The new QA matrix records the isolated shell phase, xdist fallback, and known baseline caveats.
- Any required `.gitignore` exception is added narrowly and only for the new tracked doc.

## Handoff Notes
- This is the final packet in the set.
- Keep the docs honest about unresolved baseline failures and isolation tradeoffs; do not claim that the full pytest suite is green if the serializer baseline issue remains open.
