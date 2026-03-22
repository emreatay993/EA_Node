# NODE_INLINE_TITLES P04: Docs And Traceability Closeout

## Objective
- Refresh the project docs and requirement traceability so the new shared inline-title workflow is described accurately and anchored to the packet-owned regressions.

## Preconditions
- `P03` is marked `PASS` in [NODE_INLINE_TITLES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_STATUS.md).
- No later `NODE_INLINE_TITLES` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `README.md`
- `ARCHITECTURE.md`
- `RELEASE_NOTES.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Conservative Write Scope
- `README.md`
- `ARCHITECTURE.md`
- `RELEASE_NOTES.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/node_inline_titles/P04_docs_traceability_closeout_WRAPUP.md`

## Required Behavior
- Update the architecture and user-facing docs to describe the final shared inline-title-edit workflow, including the reuse of the shared header editor and the preserved `OPEN` badge scope-entry affordance for subnode shells.
- Add or refresh requirement/acceptance language so inline title editing across node families and scoped-node scope-entry preservation are represented in the authoritative requirement docs.
- Update the traceability matrix so the packet-owned regression tests are the documented proof points for the new behavior.
- Keep this packet docs-only except for traceability-checker updates that are strictly required to make the new documentation/test mapping validate cleanly.

## Non-Goals
- No source/QML/runtime feature changes in this packet.
- No new QA matrix artifact unless the traceability update proves one is already required by existing conventions.
- No packet-external work-packet manifest edits beyond any traceability references strictly required by the updated docs.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q`
2. `./venv/Scripts/python.exe scripts/check_traceability.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/node_inline_titles/P04_docs_traceability_closeout_WRAPUP.md`

## Acceptance Criteria
- Project docs accurately describe the shared inline title editor, mutation authority, and scoped-node `OPEN` badge behavior.
- Requirement and traceability docs reference the packet-owned regressions for the new inline-title workflow.
- Traceability verification passes.
- The packet does not modify runtime code.

## Handoff Notes
- Record any new requirement or acceptance IDs explicitly in the wrap-up so future packet sets can target them without rediscovery.
- Keep the wrap-up clear about which tests became the canonical proof points for shared inline title editing.
