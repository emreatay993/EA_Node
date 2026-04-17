# MEDIA_VIEWER_CONTENT_FULLSCREEN P00: Bootstrap

## Objective

- Establish the `MEDIA_VIEWER_CONTENT_FULLSCREEN` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and ensure the new packet directory plus future wrap-ups and QA matrix are trackable.

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- The review baseline exists at [PLANS_TO_IMPLEMENT/in_progress/Media And Viewer Content Fullscreen.md](../../../../PLANS_TO_IMPLEMENT/in_progress/Media%20And%20Viewer%20Content%20Fullscreen.md).
- No `media_viewer_content_fullscreen` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies

- none

## Target Subsystems

- `docs/specs/work_packets/media_viewer_content_fullscreen/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/**`

## Required Behavior

- Create `docs/specs/work_packets/media_viewer_content_fullscreen/`.
- Add `MEDIA_VIEWER_CONTENT_FULLSCREEN_MANIFEST.md` and `MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P05` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `MEDIA_VIEWER_CONTENT_FULLSCREEN` manifest and status ledger.
- Update `.gitignore` so the new packet docs, future packet wrap-ups, and future `docs/specs/perf/MEDIA_VIEWER_CONTENT_FULLSCREEN_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md` and leave `P01` through `P05` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and wrap-up expectations aligned with the media/viewer fullscreen plan.
- Make no runtime, product-source, test, packaging-script, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals

- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `docs/specs/requirements/**` or `docs/specs/perf/**` in this packet.

## Verification Commands

1. File gate:

```powershell
@'
from pathlib import Path
import subprocess

required = [
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_MANIFEST.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P01_fullscreen_state_contract.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P01_fullscreen_state_contract_PROMPT.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P02_shell_overlay_and_media_renderer.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P02_shell_overlay_and_media_renderer_PROMPT.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P03_surface_buttons_and_shortcut.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P03_surface_buttons_and_shortcut_PROMPT.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P04_interactive_live_viewer_retargeting.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P04_interactive_live_viewer_retargeting_PROMPT.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_MANIFEST.md",
    "docs/specs/work_packets/media_viewer_content_fullscreen/P05_regression_closeout_WRAPUP.md",
    "docs/specs/perf/MEDIA_VIEWER_CONTENT_FULLSCREEN_QA_MATRIX.md",
):
    check = subprocess.run(
        ["git", "check-ignore", tracked_path],
        capture_output=True,
        text=True,
    )
    if check.returncode == 0:
        print("IGNORED: " + tracked_path)
        raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "MEDIA_VIEWER_CONTENT_FULLSCREEN Work Packet Manifest",
    "MEDIA_VIEWER_CONTENT_FULLSCREEN Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path

text = Path(
    "docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md"
).read_text(encoding="utf-8")
checks = (
    "| P00 Bootstrap | `codex/media-viewer-content-fullscreen/p00-bootstrap` | PASS |",
    "| P01 Fullscreen State Contract | `codex/media-viewer-content-fullscreen/p01-fullscreen-state-contract` | PENDING |",
    "| P02 Shell Overlay and Media Renderer | `codex/media-viewer-content-fullscreen/p02-shell-overlay-and-media-renderer` | PENDING |",
    "| P03 Surface Buttons and Shortcut | `codex/media-viewer-content-fullscreen/p03-surface-buttons-and-shortcut` | PENDING |",
    "| P04 Interactive Live Viewer Retargeting | `codex/media-viewer-content-fullscreen/p04-interactive-live-viewer-retargeting` | PENDING |",
    "| P05 Regression Closeout | `codex/media-viewer-content-fullscreen/p05-regression-closeout` | PENDING |",
)
for needle in checks:
    if needle not in text:
        print("STATUS_MISSING: " + needle)
        raise SystemExit(1)
print("MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_MANIFEST.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P01_fullscreen_state_contract.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P01_fullscreen_state_contract_PROMPT.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P02_shell_overlay_and_media_renderer.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P02_shell_overlay_and_media_renderer_PROMPT.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P03_surface_buttons_and_shortcut.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P03_surface_buttons_and_shortcut_PROMPT.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P04_interactive_live_viewer_retargeting.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P04_interactive_live_viewer_retargeting_PROMPT.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout_PROMPT.md`

## Acceptance Criteria

- The file-gate command returns `MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_FILE_GATE_PASS`.
- The review gate returns `MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_STATUS_PASS`.
- `MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `media_viewer_content_fullscreen` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
