# TITLE_ICONS_FOR_NON_PASSIVE_NODES P05: Verification Docs Traceability Closeout

## Objective
- Publish retained QA evidence, requirement updates, and traceability closeout for the shipped path-based title-icons feature after implementation packets are accepted.

## Preconditions
- `P01` is marked `PASS` in [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md).
- `P02` is marked `PASS` in [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md).
- `P03` is marked `PASS` in [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md).
- `P04` is marked `PASS` in [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md).
- No later `TITLE_ICONS_FOR_NON_PASSIVE_NODES` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`
- `P04`

## Target Subsystems
- `docs/specs/INDEX.md`
- `docs/specs/perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Conservative Write Scope
- `docs/specs/INDEX.md`
- `docs/specs/perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P05_verification_docs_traceability_closeout_WRAPUP.md`

## Required Behavior
- Add retained QA evidence for the full feature at `docs/specs/perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md`.
- Update requirement docs only where needed to document:
  - path-only node-title icon rendering for active and `compile_only` nodes
  - passive title-icon exclusion
  - local-file-only resolver behavior and supported suffixes
  - app-global nullable icon-size override
  - built-in node-title icon asset packaging
  - preservation of collapsed comment-backdrop icon behavior
- Update `TRACEABILITY_MATRIX.md` with the relevant requirement-to-test mapping.
- Update `docs/specs/INDEX.md` with the QA matrix link if it is not already listed.
- Update `tests/test_traceability_checker.py` only if a new retained QA matrix or traceability token requires it.
- Do not reopen runtime, QML, settings, asset, or built-in node code.
- Add manual validation notes for real Windows desktop rendering:
  - SVG, PNG/JPG/JPEG fixture coverage where available
  - active and `compile_only` node title icons
  - passive nodes staying iconless
  - centered and elided title behavior
  - collapsed comment-backdrop icon unchanged
  - icon-size override automatic and explicit modes

## Non-Goals
- No product-source changes under `ea_node_editor/**`.
- No implementation-test changes except traceability checker maintenance.
- No new icon assets.
- No changes to packet specs outside status-ledger closeout unless required for a traceability correction.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q`
2. `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Review Gate
- `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P05_verification_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md`

## Acceptance Criteria
- The QA matrix captures all implementation packet verification and any manual rendering evidence.
- Requirement docs describe the shipped title-icon contract without contradicting passive-node, app-preference, or persistence requirements.
- Traceability checker tests pass.
- `scripts/check_traceability.py` passes.
- No runtime/source files are changed in this closeout packet.

## Handoff Notes
- This is the final implementation packet. When P05 is accepted, the executor reports the accepted packet branches and waits for a user-triggered merge into the target branch.
- Any future expansion to node-library or inspector icon rendering should be planned as a separate packet set.
