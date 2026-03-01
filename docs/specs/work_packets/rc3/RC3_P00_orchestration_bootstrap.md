# RC3 P00: Orchestration Bootstrap

## Objective
- Establish RC3 packet contracts/prompts, initialize the RC3 status ledger, and register RC3 docs in the canonical spec index.

## Non-Objectives
- No runtime behavior, UI behavior, execution engine, or persistence code changes.
- No requirement text rewrites in `docs/specs/requirements/*`.

## Inputs
- `docs/specs/work_packets/rc2/RC2_MANIFEST.md`
- `docs/specs/work_packets/rc2/RC2_STATUS.md`
- `docs/specs/INDEX.md`

## Allowed Files
- `docs/specs/work_packets/rc3/*`
- `docs/specs/INDEX.md`

## Do Not Touch
- `ea_node_editor/**`
- `tests/**`
- `scripts/**`
- `docs/specs/requirements/**`

## Verification
1. `& { $required = @('docs/specs/work_packets/rc3/RC3_MANIFEST.md','docs/specs/work_packets/rc3/RC3_STATUS.md','docs/specs/work_packets/rc3/RC3_P00_orchestration_bootstrap.md','docs/specs/work_packets/rc3/RC3_P00_orchestration_bootstrap_PROMPT.md','docs/specs/work_packets/rc3/RC3_P01_process_streaming.md','docs/specs/work_packets/rc3/RC3_P01_process_streaming_PROMPT.md','docs/specs/work_packets/rc3/RC3_P02_script_editor_ergonomics.md','docs/specs/work_packets/rc3/RC3_P02_script_editor_ergonomics_PROMPT.md','docs/specs/work_packets/rc3/RC3_P03_desktop_perf_baselines.md','docs/specs/work_packets/rc3/RC3_P03_desktop_perf_baselines_PROMPT.md','docs/specs/work_packets/rc3/RC3_P04_dependency_packaging_policy.md','docs/specs/work_packets/rc3/RC3_P04_dependency_packaging_policy_PROMPT.md','docs/specs/work_packets/rc3/RC3_P05_installer_pipeline.md','docs/specs/work_packets/rc3/RC3_P05_installer_pipeline_PROMPT.md','docs/specs/work_packets/rc3/RC3_P06_signing_and_verification.md','docs/specs/work_packets/rc3/RC3_P06_signing_and_verification_PROMPT.md','docs/specs/work_packets/rc3/RC3_P07_pilot_readiness.md','docs/specs/work_packets/rc3/RC3_P07_pilot_readiness_PROMPT.md','docs/specs/work_packets/rc3/RC3_P08_qa_traceability.md','docs/specs/work_packets/rc3/RC3_P08_qa_traceability_PROMPT.md'); $missing = $required | Where-Object { -not (Test-Path $_) }; if ($missing) { Write-Output ('MISSING: ' + ($missing -join ', ')); exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'RC3 Work Packet Manifest' -Quiet)) { Write-Output 'INDEX_MISSING_RC3_MANIFEST'; exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'RC3 Status Ledger' -Quiet)) { Write-Output 'INDEX_MISSING_RC3_STATUS'; exit 1 }; Write-Output 'RC3_P00_FILE_GATE_PASS' }`

## Output Artifacts
- `docs/specs/work_packets/rc3/RC3_MANIFEST.md`
- `docs/specs/work_packets/rc3/RC3_STATUS.md`
- `docs/specs/work_packets/rc3/RC3_P00_orchestration_bootstrap.md`
- `docs/specs/work_packets/rc3/RC3_P00_orchestration_bootstrap_PROMPT.md`
- `docs/specs/work_packets/rc3/RC3_P01_process_streaming.md`
- `docs/specs/work_packets/rc3/RC3_P01_process_streaming_PROMPT.md`
- `docs/specs/work_packets/rc3/RC3_P02_script_editor_ergonomics.md`
- `docs/specs/work_packets/rc3/RC3_P02_script_editor_ergonomics_PROMPT.md`
- `docs/specs/work_packets/rc3/RC3_P03_desktop_perf_baselines.md`
- `docs/specs/work_packets/rc3/RC3_P03_desktop_perf_baselines_PROMPT.md`
- `docs/specs/work_packets/rc3/RC3_P04_dependency_packaging_policy.md`
- `docs/specs/work_packets/rc3/RC3_P04_dependency_packaging_policy_PROMPT.md`
- `docs/specs/work_packets/rc3/RC3_P05_installer_pipeline.md`
- `docs/specs/work_packets/rc3/RC3_P05_installer_pipeline_PROMPT.md`
- `docs/specs/work_packets/rc3/RC3_P06_signing_and_verification.md`
- `docs/specs/work_packets/rc3/RC3_P06_signing_and_verification_PROMPT.md`
- `docs/specs/work_packets/rc3/RC3_P07_pilot_readiness.md`
- `docs/specs/work_packets/rc3/RC3_P07_pilot_readiness_PROMPT.md`
- `docs/specs/work_packets/rc3/RC3_P08_qa_traceability.md`
- `docs/specs/work_packets/rc3/RC3_P08_qa_traceability_PROMPT.md`

## Merge Gate (Requirement IDs)
- `REQ-QA-001`
- `AC-REQ-QA-001-01`
- Verification command returns `RC3_P00_FILE_GATE_PASS`.
- `RC3_STATUS.md` marks `P00` as `PASS` with branch label and command history.
