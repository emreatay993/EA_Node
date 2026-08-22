# ANSYS_DPF_FULL_PLUGIN_ROLLOUT P07: Verification Docs Closeout

## Objective

- Publish the retained QA, requirements, architecture, and closeout evidence for the DPF full-plugin rollout after the implementation packets land.

## Preconditions

- `P06` is marked `PASS` in [ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md](./ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md).
- No later `ANSYS_DPF_FULL_PLUGIN_ROLLOUT` packet is in progress.

## Execution Dependencies

- `P06`

## Target Subsystems

- `ARCHITECTURE.md`
- `README.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`

## Conservative Write Scope

- `ARCHITECTURE.md`
- `README.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P07_verification_docs_closeout_WRAPUP.md`

## Required Behavior

- Publish a QA matrix that captures the rollout's retained proof and packet-owned regression anchors.
- Update architecture and integration docs so the workflow-first DPF taxonomy, version-aware plugin lifecycle, generated operator rollout, helper rollout, and missing-plugin behavior are documented.
- Update requirements and traceability docs so the rollout is anchored in the repo's retained requirement set.
- Keep the closeout proof focused on retained packet evidence rather than reopening already-proven implementation seams.

## Non-Goals

- No new code-path rollout beyond the doc or traceability work needed to describe shipped behavior.
- No broad rerun of unrelated repo-wide verification.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py --ignore=venv -q
.\venv\Scripts\python.exe scripts/check_traceability.py
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_traceability.py
```

## Expected Artifacts

- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P07_verification_docs_closeout_WRAPUP.md`
- `docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md`
- `ARCHITECTURE.md`
- `README.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`

## Acceptance Criteria

- The rollout has a retained QA matrix and closeout docs that match the implemented packet boundaries.
- Requirements and traceability docs reflect the workflow-first taxonomy, version-aware plugin lifecycle, and generated DPF rollout.
- Closeout regression anchors pass.

## Handoff Notes

- This is the terminal packet for the rollout. Any literal raw API mirror follow-up must start as a new plan and packet set.
