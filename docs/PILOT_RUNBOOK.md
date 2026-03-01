# Pilot Runbook

## Scope

- Audience: internal pilot operators validating packaged desktop build `EA_Node_Editor.exe`.
- Release: `EA_Node_Editor_RC1_2026-03-01`.
- Package root: `artifacts/releases/EA_Node_Editor_RC1_2026-03-01/`.

## Install And Start

1. Open PowerShell in repository root.
2. Confirm executable exists:
   `Test-Path artifacts\releases\EA_Node_Editor_RC1_2026-03-01\dist\EA_Node_Editor\EA_Node_Editor.exe`
3. (Recommended) Validate checksum:
   `Get-FileHash artifacts\releases\EA_Node_Editor_RC1_2026-03-01\dist\EA_Node_Editor\EA_Node_Editor.exe -Algorithm SHA256`
   Compare with `artifacts\releases\EA_Node_Editor_RC1_2026-03-01\EA_Node_Editor.exe.sha256`.
4. Launch app:
   `.\artifacts\releases\EA_Node_Editor_RC1_2026-03-01\dist\EA_Node_Editor\EA_Node_Editor.exe`
5. Wait for main window and verify the status bar initializes to an idle/ready state.

## Smoke Workflows

1. Workspace and graph setup
   - Create a new workspace and a new view.
   - Add `Start`, `Logger`, `End` nodes.
   - Connect `Start -> Logger -> End`.
   - Pass criteria: nodes and edges appear correctly; no error dialog.
2. Simple execution flow
   - Run `Start -> Logger -> End`.
   - Pass criteria: execution completes and status returns to `Ready (Completed)`.
3. File pipeline flow
   - Build `File Read -> Python Script -> File Write`.
   - Use small text input and script transform (for example uppercase).
   - Pass criteria: output file is written and output content matches expected transform.
4. Controlled failure UX
   - In `Python Script`, intentionally raise an error.
   - Run flow and observe UI.
   - Pass criteria: `Workflow Error` dialog appears; failed node is focused/inspectable.
5. Save, reopen, recovery behavior
   - Save project as `.sfe`, close app, relaunch app.
   - Accept recovery prompt when prompted.
   - Pass criteria: prior tabs/views restore and unsaved recovery graph is restored after acceptance.

## Failure Reporting Template

Use this template in pilot issue reports:

```text
Title: [Pilot][RC1] <short failure title>
Date/Time (UTC): <YYYY-MM-DDTHH:MM:SSZ>
Operator: <name>
Build Label: EA_Node_Editor_RC1_2026-03-01
Executable Path: artifacts/releases/EA_Node_Editor_RC1_2026-03-01/dist/EA_Node_Editor/EA_Node_Editor.exe
Workflow: <1-5 from runbook>
Expected Result: <expected behavior>
Actual Result: <observed behavior>
Repro Steps:
1) ...
2) ...
3) ...
Artifacts:
- Screenshot(s): <path>
- Console/log text: <path or pasted excerpt>
- Sample project/input files: <path>
Severity: <P0/P1/P2>
```

## Rollback Instructions

1. Stop pilot usage of RC1 executable.
2. Announce rollback in pilot channel with timestamp and reason.
3. Switch launch target to last approved packaged build location.
4. Archive failing RC1 evidence under `artifacts/pilot_signoff/<new_run_id>/`.
5. Update `docs/specs/perf/PILOT_BACKLOG.md` with failure summary and blocker classification.
6. Do not resume RC1 pilot until a new sign-off run records decision `GO`.
