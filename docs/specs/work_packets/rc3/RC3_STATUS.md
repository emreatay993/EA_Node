# RC3 Status Ledger

- Updated: `2026-03-01`
- Environment note: outer repo baseline `f40a913`; inner package repo baseline `d7a3009`.

| Packet | Branch Label | Status | Commit SHA | Commands | Tests | Artifacts | Residual Risks |
|---|---|---|---|---|---|---|---|
| P00 Orchestration | `rc3/p00-orchestration` | PASS | `pending` | `New-Item -ItemType Directory docs/specs/work_packets/rc3` + scaffold `RC3_MANIFEST.md`, `RC3_STATUS.md`, `RC3_P00..P08*.md`; rewrite `docs/specs/INDEX.md` + run `& { $required = @(...) ; ... ; Write-Output 'RC3_P00_FILE_GATE_PASS' }` | PASS (`1/1`): RC3 file/index gate command returned `RC3_P00_FILE_GATE_PASS` | `docs/specs/work_packets/rc3/*`, `docs/specs/INDEX.md` | none |
| P01 Process Streaming | `rc3/p01-process-streaming` | TODO | `n/a` | pending | pending | pending | stream event schema drift |
| P02 Script Editor Ergonomics | `rc3/p02-script-editor-ergonomics` | TODO | `n/a` | pending | pending | pending | UI regression risk in dock focus/shortcuts |
| P03 Desktop Perf Baselines | `rc3/p03-desktop-perf-baselines` | TODO | `n/a` | pending | pending | pending | hardware variance across pilot machines |
| P04 Dependency Packaging Policy | `rc3/p04-dependency-packaging-policy` | TODO | `n/a` | pending | pending | pending | optional dependency behavior may diverge packaged vs venv |
| P05 Installer Pipeline | `rc3/p05-installer-pipeline` | TODO | `n/a` | pending | pending | pending | unsigned installer trust prompts |
| P06 Signing and Verification | `rc3/p06-signing-and-verification` | TODO | `n/a` | pending | pending | pending | certificate handling and timestamp availability |
| P07 Pilot Readiness | `rc3/p07-pilot-readiness` | TODO | `n/a` | pending | pending | pending | operator environment drift |
| P08 QA and Traceability | `rc3/p08-qa-traceability` | TODO | `n/a` | pending | pending | pending | full-suite duration and flaky environment dependencies |
