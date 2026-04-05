# UI_CONTEXT_SCALABILITY_FOLLOWUP P00: Bootstrap

## Objective

- Establish the `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet set, write the follow-up review baseline, initialize the status ledger, register the new packet set in the spec index, and ensure the packet docs, future wrap-ups, and future QA matrix are trackable.

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- No `ui_context_scalability_followup` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies

- `none`

## Target Subsystems

- `docs/UI_CONTEXT_SCALABILITY_FOLLOWUP_REVIEW_2026-04-05.md`
- `docs/specs/work_packets/ui_context_scalability_followup/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope

- `.gitignore`
- `docs/UI_CONTEXT_SCALABILITY_FOLLOWUP_REVIEW_2026-04-05.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/ui_context_scalability_followup/**`

## Required Behavior

- Create `docs/UI_CONTEXT_SCALABILITY_FOLLOWUP_REVIEW_2026-04-05.md` as the stable review baseline for this packet set.
- Add `UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md` and `UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P09` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `UI_CONTEXT_SCALABILITY_FOLLOWUP` manifest and status ledger.
- Update `.gitignore` so the new packet docs, future packet wrap-ups, and future `docs/specs/perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md` and leave `P01` through `P09` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and wrap-up expectations aligned with the repo's tracked work-packet conventions.
- Make no runtime, product-source, test, packaging-script, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals

- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `ARCHITECTURE.md`, `README.md`, or `docs/specs/requirements/**` in this packet.

## Verification Commands

1. File and tracking gate:

```powershell
@'
from pathlib import Path
import subprocess

required = [
    "docs/UI_CONTEXT_SCALABILITY_FOLLOWUP_REVIEW_2026-04-05.md",
    "docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md",
    "docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md",
]
slugs = [
    "P00_bootstrap",
    "P01_guardrail_catalog_expansion",
    "P02_shell_session_surface_split",
    "P03_graph_geometry_facade_split",
    "P04_graph_scene_mutation_packet_split",
    "P05_main_window_bridge_test_packetization",
    "P06_graph_surface_test_packetization",
    "P07_track_b_test_packetization",
    "P08_canonical_ui_test_packet_docs",
    "P09_verification_docs_closeout",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md",
    "docs/specs/work_packets/ui_context_scalability_followup/P09_verification_docs_closeout_WRAPUP.md",
    "docs/specs/perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md",
):
    check = subprocess.run(
        ["git", "check-ignore", tracked_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode == 0:
        print("IGNORED: " + tracked_path)
        raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "UI_CONTEXT_SCALABILITY_FOLLOWUP Work Packet Manifest",
    "UI_CONTEXT_SCALABILITY_FOLLOWUP Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("UI_CONTEXT_SCALABILITY_FOLLOWUP_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path
text = Path(
    "docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md"
).read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/ui-context-scalability-followup/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("UI_CONTEXT_SCALABILITY_FOLLOWUP_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `.gitignore`
- `docs/UI_CONTEXT_SCALABILITY_FOLLOWUP_REVIEW_2026-04-05.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md`
- `docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md`
- `docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_P*.md`
- `docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_P*_PROMPT.md`

## Acceptance Criteria

- The verification command returns `UI_CONTEXT_SCALABILITY_FOLLOWUP_P00_FILE_GATE_PASS`.
- The review gate returns `UI_CONTEXT_SCALABILITY_FOLLOWUP_P00_STATUS_PASS`.
- `UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/UI_CONTEXT_SCALABILITY_FOLLOWUP_REVIEW_2026-04-05.md`, `docs/specs/INDEX.md`, and the new `ui_context_scalability_followup` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
