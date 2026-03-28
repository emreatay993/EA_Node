# Architecture Refactor QA Matrix

- Updated: `2026-03-27`
- Packet set: `ARCHITECTURE_REFACTOR` (`P01` through `P13`)
- Scope: final docs, release, traceability, and Windows-follow-up closeout for
  the architecture refactor packet set.

## Locked Scope

- `docs/PACKAGING_WINDOWS.md`, `docs/PILOT_RUNBOOK.md`, `docs/specs/INDEX.md`,
  and this matrix are the canonical active release and closeout docs on this
  branch.
- `scripts/check_traceability.py` is the semantic guardrail for canonical-doc
  drift, and `scripts/check_markdown_links.py` is the local-link hygiene gate.
- `tests/test_packaging_configuration.py` and `tests/test_markdown_hygiene.py`
  are the packet-owned regression checks for release-script truth and markdown
  hygiene.
- `docs/specs/perf/RC_PACKAGING_REPORT.md` and
  `docs/specs/perf/PILOT_SIGNOFF.md` remain archived evidence only; they do not
  substitute for fresh packaging, signing, or pilot proof after the refactor.

## Final Verification Commands

| Coverage Area | Command | Expected Coverage |
|---|---|---|
| Final packet regression | `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py tests/test_traceability_checker.py tests/test_packaging_configuration.py tests/test_dead_code_hygiene.py tests/test_markdown_hygiene.py --ignore=venv -q` | Revalidates the packet-owned verification manifest, traceability checker, packaging/signing configuration, dead-code hygiene guard, and markdown-link contract |
| Traceability gate | `./venv/Scripts/python.exe scripts/check_traceability.py` | Confirms the canonical architecture, release, pilot, spec-index, QA-matrix, and archived-evidence docs stay aligned |
| Markdown link gate | `./venv/Scripts/python.exe scripts/check_markdown_links.py` | Confirms the active canonical Markdown docs only reference existing local targets and valid heading anchors |

## Focused Narrow Reruns

| Coverage Area | Command | When To Use It |
|---|---|---|
| Packaging and signing truth | `./venv/Scripts/python.exe -m pytest tests/test_packaging_configuration.py tests/test_markdown_hygiene.py --ignore=venv -q` | Use after editing `pyproject.toml`, `ea_node_editor.spec`, Windows packaging scripts, or the packaging guide |
| Traceability and final QA matrix | `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py --ignore=venv -q` | Use after editing `ARCHITECTURE.md`, `docs/specs/INDEX.md`, requirements docs, perf matrices, or traceability rows |
| Semantic proof audit | `./venv/Scripts/python.exe scripts/check_traceability.py` | Use as the review gate after any canonical-doc, requirements, or QA-matrix edit |
| Markdown links only | `./venv/Scripts/python.exe scripts/check_markdown_links.py` | Use after editing local Markdown links, especially spec-index, packaging, pilot, and final QA-matrix references |

## 2026-03-27 Execution Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py tests/test_traceability_checker.py tests/test_packaging_configuration.py tests/test_dead_code_hygiene.py tests/test_markdown_hygiene.py --ignore=venv -q` | PASS | Packet-owned doc, packaging, and traceability regression suite passed in the project venv |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Canonical-doc drift audit passed after the packaging, pilot, spec-index, requirements, and final QA-matrix refresh |
| `./venv/Scripts/python.exe scripts/check_markdown_links.py` | PASS | Active canonical Markdown docs resolved to existing local targets and valid headings |

## Remaining Manual and Windows-Only Checks

1. Base packaging rerun: execute `.\scripts\build_windows_package.ps1 -PackageProfile base -Clean`, confirm `artifacts\pyinstaller\dist\base\COREX_Node_Editor\COREX_Node_Editor.exe` exists, and preserve the generated dependency matrix under `artifacts\releases\packaging\base\`.
2. Base installer rerun: execute `.\scripts\build_windows_installer.ps1 -PackageProfile base`, then confirm the latest `installer_manifest.json` and `installer_validation.json` under `artifacts\releases\installer\base\<run_id>\` record `package_profile: base`.
3. Signing rerun with real certificate material: execute `.\scripts\sign_release_artifacts.ps1 -PackageProfile base -VerifyOnly` for snapshot capture, then rerun with `-CertThumbprint` and `-TimestampServer` when release credentials are available.
4. Viewer-profile packaging follow-up: on a workstation with `.[ansys,viewer]` or `.[dev]`, rerun the package, installer, and signing flow with `-PackageProfile viewer`.
5. Pilot rerun: follow `docs/PILOT_RUNBOOK.md` against a freshly built packaged candidate and record new evidence instead of reusing archived 2026-03-01 snapshots.

## Archived Evidence Boundaries

- `docs/specs/perf/RC_PACKAGING_REPORT.md` is an archived 2026-03-01 packaging smoke snapshot kept for historical context only.
- `docs/specs/perf/PILOT_SIGNOFF.md` is an archived 2026-03-01 packaged desktop pilot snapshot kept for historical context only.
- Neither archived report is current release sign-off. Fresh package, installer, signing, and pilot proof must come from the active scripts and runbook above.

## Residual Risks

- Windows packaging, installer, signing, and pilot reruns remain host-specific manual follow-ups and were not re-executed in this packet.
- Viewer-profile packaging still depends on optional PyDPF and PyVista runtime availability in the build venv.
- The final doc guardrails now catch stale canonical links and drift, but they do not manufacture fresh Windows artifact evidence by themselves.
