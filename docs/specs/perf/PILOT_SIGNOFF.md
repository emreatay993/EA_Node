# Pilot Sign-off Report

- Updated: `2026-03-18`
- Evidence Status: Archived packaged desktop pilot sign-off restored from repo
  history after the checked-in report disappeared from the current proof layer.
- Historical Run Window (UTC): `2026-03-01T18:15:23Z` to `2026-03-01T18:18:51Z`
- Evidence Run Id: `20260301_211523`
- Current Constraint: P08 did not rerun the packaged pilot. The historical
  `artifacts/pilot_signoff/20260301_211523/` screenshot and JSON bundle is not
  retained in this checkout, so rerun [docs/PILOT_RUNBOOK.md](../../PILOT_RUNBOOK.md)
  before treating this as current sign-off evidence.

## Archived 2026-03-01 Snapshot

- Scope: packaged desktop pilot validation only (`EA_Node_Editor.exe`)
- Executable: `artifacts/pyinstaller/dist/EA_Node_Editor/EA_Node_Editor.exe`
- Executable SHA-256:
  `c76a8c5c658488c0cf57e363f3e0892617348214f2e97b70318c0994ec3181d5`
- Environment: `Windows-10-10.0.26200-SP0`, `Python 3.10.0`, `AMD64`

### Flow Verdicts

| Requested flow | Result | Historical Evidence Bundle Path |
|---|---|---|
| Open app, create workspace/view, add nodes, connect nodes | PASS | `artifacts/pilot_signoff/20260301_211523/screenshots/01_workspace_view_add_connect_attempt.png` |
| Run simple workflow (`Start -> Logger -> End`) | PASS | `artifacts/pilot_signoff/20260301_211523/screenshots/02_simple_workflow_completed.png` |
| Run file pipeline (`File Read -> Python Script -> File Write`) | PASS | `artifacts/pilot_signoff/20260301_211523/screenshots/03_file_pipeline_completed.png` |
| Controlled failure + node focus/error UX | PASS | `artifacts/pilot_signoff/20260301_211523/screenshots/04_failure_error_dialog.png` |
| Save `.sfe`, close, reopen, restore/recovery behavior | PASS | `artifacts/pilot_signoff/20260301_211523/screenshots/05_recovery_prompt.png`, `artifacts/pilot_signoff/20260301_211523/screenshots/06_recovered_state.png` |

### Notes By Flow

1. Workspace/view/add/connect:
   - Workspace creation: PASS.
   - View creation: PASS.
   - Add/connect validation: PASS.
   - Observation: inspector moved to the newly added node after add attempts.
2. Simple workflow:
   - Engine state reached `Ready (Completed)`.
3. File pipeline:
   - Engine state reached `Ready (Completed)`.
   - Output file produced and content matched the expected uppercase transform.
4. Controlled failure UX:
   - `Workflow Error` dialog surfaced with the expected script error text.
   - Inspector text after failure showed the failed node focus behavior.
5. Save/reopen/restore/recovery:
   - Save/reopen restore: PASS.
   - Recovery prompt path: PASS.
   - Recovery acceptance state: PASS.

## Final Pilot Decision

- Historical decision: **GO** for internal pilot on the archived `2026-03-01`
  evidence run.
