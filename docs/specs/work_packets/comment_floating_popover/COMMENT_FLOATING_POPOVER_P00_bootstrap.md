# COMMENT_FLOATING_POPOVER P00: Bootstrap

## Objective

- Establish the `COMMENT_FLOATING_POPOVER` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and bootstrap a fresh-context plan for the COREX comment floating popover work defined in [PLANS_TO_IMPLEMENT/in_progress/COREX Comment Floating Popover Plan.md](../../../../PLANS_TO_IMPLEMENT/in_progress/COREX%20Comment%20Floating%20Popover%20Plan.md).

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- `docs/specs/work_packets/comment_floating_popover/` is either absent or contains only local bootstrap-planning artifacts that are not yet registered in the canonical spec index.

## Execution Dependencies

- none

## Target Subsystems

- `docs/specs/work_packets/comment_floating_popover/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope

- `docs/specs/INDEX.md`
- `docs/specs/work_packets/comment_floating_popover/**`

## Required Behavior

- Create or refresh `docs/specs/work_packets/comment_floating_popover/`.
- Add `COMMENT_FLOATING_POPOVER_MANIFEST.md` and `COMMENT_FLOATING_POPOVER_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P03` using the current work-packet naming convention.
- Update `docs/specs/INDEX.md` with links to the `COMMENT_FLOATING_POPOVER` manifest and status ledger.
- Mark `P00` as `PASS` in `COMMENT_FLOATING_POPOVER_STATUS.md` and leave `P01` through `P03` as `PENDING`.
- Preserve the source-plan packet split: `P01` owns the overlay shell, `P02` owns the comment-specific action wiring and body commit route, and `P03` owns the regression/verification closeout.
- Encode the packet-set worker model override: implementation workers must use `gpt-5.5` with `xhigh` reasoning.
- Make no runtime, product-source, test, packaging-script, performance-doc, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals

- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `docs/specs/perf/**` or `docs/specs/requirements/**` in this packet.
- No implementation of `P01`, `P02`, or `P03` behavior in this packet.

## Verification Commands

1. File gate:

```powershell
@'
from pathlib import Path

slugs = [
    "P00_bootstrap",
    "P01_overlay_shell",
    "P02_action_wiring_and_commit_flow",
    "P03_tests_and_verification",
]
required = [
    "docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_MANIFEST.md",
    "docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_STATUS.md",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "COMMENT_FLOATING_POPOVER Work Packet Manifest",
    "COMMENT_FLOATING_POPOVER Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("COMMENT_FLOATING_POPOVER_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path
text = Path("docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_STATUS.md").read_text(encoding="utf-8")
required = [
    "| P00 Bootstrap | `codex/comment-floating-popover/p00-bootstrap` | PASS |",
    "| P01 Overlay Shell | `codex/comment-floating-popover/p01-overlay-shell` | PENDING |",
    "| P02 Action Wiring and Commit Flow | `codex/comment-floating-popover/p02-action-wiring-and-commit-flow` | PENDING |",
    "| P03 Tests and Verification | `codex/comment-floating-popover/p03-tests-and-verification` | PENDING |",
    "Worker model override: implementation workers for `P01` through `P03` use `gpt-5.5` with `xhigh` reasoning.",
]
for needle in required:
    if needle not in text:
        print("STATUS_MISSING: " + needle)
        raise SystemExit(1)
print("COMMENT_FLOATING_POPOVER_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `docs/specs/INDEX.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_MANIFEST.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_STATUS.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_P00_bootstrap.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_P01_overlay_shell.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_P01_overlay_shell_PROMPT.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_P02_action_wiring_and_commit_flow.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_P02_action_wiring_and_commit_flow_PROMPT.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_P03_tests_and_verification.md`
- `docs/specs/work_packets/comment_floating_popover/COMMENT_FLOATING_POPOVER_P03_tests_and_verification_PROMPT.md`

## Acceptance Criteria

- The verification command returns `COMMENT_FLOATING_POPOVER_P00_FILE_GATE_PASS`.
- The review gate returns `COMMENT_FLOATING_POPOVER_P00_STATUS_PASS`.
- `COMMENT_FLOATING_POPOVER_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The manifest and fresh-thread prompt both state that implementation workers use `gpt-5.5` with `xhigh` reasoning.
- The only modified tracked paths are `docs/specs/INDEX.md` and the `comment_floating_popover` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- Executor-created worktrees need these packet docs to exist on the target merge branch. If the bootstrap docs are still uncommitted, commit or merge them before starting implementation execution.
