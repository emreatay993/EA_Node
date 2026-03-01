# RC2 Work Packet Manifest

- Date: `2026-03-01`
- Scope baseline: Stitch-first UX RC2
- Canonical requirements: [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- ADRs: [docs/specs/adrs](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/adrs)

## Packet Order (Strict)

1. `RC2_P01_shell_theme.md`
2. `RC2_P02_canvas_visuals.md`
3. `RC2_P03_library_inspector.md`
4. `RC2_P04_schema_settings.md`
5. `RC2_P05_script_editor.md`
6. `RC2_P06_decorator_sdk.md`
7. `RC2_P07_process_node.md`
8. `RC2_P08_qa_traceability.md`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `RC2_Pxx_<name>.md`
- Implementation prompt: `RC2_Pxx_<name>_PROMPT.md`
- Status ledger update in [RC2_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/rc2/RC2_STATUS.md):
  - branch label
  - commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Packet Template Rules

- Include objective, non-objectives, explicit in-scope files, explicit do-not-touch files.
- Include exact verification commands.
- Include acceptance gate mapped to requirement IDs.
- Include output artifacts and expected file paths.
- Do not start packet `N+1` before packet `N` gate is marked `PASS` in status ledger.

