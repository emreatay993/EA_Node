# RC3 Work Packet Manifest

- Date: `2026-03-01`
- Scope baseline: Release-readiness hardening and pilot-production bridge
- Canonical requirements: [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- ADRs: [docs/specs/adrs](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/adrs)
- Precondition: RC2 packets are all `PASS` in [RC2_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/rc2/RC2_STATUS.md)

## Packet Order (Strict)

1. `RC3_P00_orchestration_bootstrap.md`
2. `RC3_P01_process_streaming.md`
3. `RC3_P02_script_editor_ergonomics.md`
4. `RC3_P03_desktop_perf_baselines.md`
5. `RC3_P04_dependency_packaging_policy.md`
6. `RC3_P05_installer_pipeline.md`
7. `RC3_P06_signing_and_verification.md`
8. `RC3_P07_pilot_readiness.md`
9. `RC3_P08_qa_traceability.md`
10. `RC3_P09_qml_cutover.md`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `RC3_Pxx_<name>.md`
- Implementation prompt: `RC3_Pxx_<name>_PROMPT.md`
- Status ledger update in [RC3_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/rc3/RC3_STATUS.md):
  - branch label
  - commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Packet Template Rules

- Include objective and non-objectives.
- Include explicit in-scope files and explicit do-not-touch files.
- Include exact verification commands.
- Include acceptance gate mapped to requirement IDs.
- Include output artifacts and expected file paths.
- Do not start packet `N+1` before packet `N` gate is marked `PASS` in status ledger.
