# GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK P00: Bootstrap

## Objective

- Establish the `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK` packet set, initialize the status ledger, register the packet docs in the canonical spec index, connect the source-of-truth plan baseline, and ensure the new packet directory plus future wrap-ups and QA matrix are trackable.

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- The review baseline exists at [PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md](../../../../PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md).
- No `global_expand_collision_avoidance_and_comment_peek` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies

- none

## Target Subsystems

- `PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope

- `PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md`
- `docs/specs/INDEX.md`
- `.gitignore`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/**`

## Required Behavior

- Create `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/`.
- Add `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md` and `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P03` using the canonical naming convention.
- Keep [PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md](../../../../PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md) as the review baseline and single source of truth for the packetized plan.
- Update `docs/specs/INDEX.md` with links to the `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK` manifest and status ledger.
- Update `.gitignore` so the new packet docs, future packet wrap-ups, and future `docs/specs/perf/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md` and leave `P01` through `P03` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and wrap-up expectations aligned with the source-of-truth plan.
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
    "PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_bootstrap.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P01_preferences_and_graphics_settings.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P01_preferences_and_graphics_settings_PROMPT.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P02_expand_collision_avoidance.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P02_expand_collision_avoidance_PROMPT.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P03_comment_peek_mode.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P03_comment_peek_mode_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md",
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/P03_comment_peek_mode_WRAPUP.md",
    "docs/specs/perf/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_QA_MATRIX.md",
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
    "GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK Work Packet Manifest",
    "GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path

text = Path(
    "docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md"
).read_text(encoding="utf-8")
checks = (
    "| P00 Bootstrap | `codex/global-expand-collision-avoidance-and-comment-peek/p00-bootstrap` | PASS |",
    "| P01 Preferences and Graphics Settings | `codex/global-expand-collision-avoidance-and-comment-peek/p01-preferences-and-graphics-settings` | PENDING |",
    "| P02 Expand Collision Avoidance | `codex/global-expand-collision-avoidance-and-comment-peek/p02-expand-collision-avoidance` | PENDING |",
    "| P03 Comment Peek Mode | `codex/global-expand-collision-avoidance-and-comment-peek/p03-comment-peek-mode` | PENDING |",
)
for needle in checks:
    if needle not in text:
        print("STATUS_MISSING: " + needle)
        raise SystemExit(1)
print("GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md`
- `docs/specs/INDEX.md`
- `.gitignore`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_bootstrap.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P01_preferences_and_graphics_settings.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P01_preferences_and_graphics_settings_PROMPT.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P02_expand_collision_avoidance.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P02_expand_collision_avoidance_PROMPT.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P03_comment_peek_mode.md`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P03_comment_peek_mode_PROMPT.md`

## Acceptance Criteria

- The file-gate command returns `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_FILE_GATE_PASS`.
- The review gate returns `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_STATUS_PASS`.
- `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md`, `docs/specs/INDEX.md`, `.gitignore`, and the new `global_expand_collision_avoidance_and_comment_peek` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
