# TOOLTIP_MANAGER P00: Bootstrap

## Objective
- Establish the `TOOLTIP_MANAGER` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and bootstrap a fresh-context plan for the tooltip policy work defined in [PLANS_TO_IMPLEMENT/in_progress/tooltip_manager.md](../../../../PLANS_TO_IMPLEMENT/in_progress/tooltip_manager.md).

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- `docs/specs/work_packets/tooltip_manager/` is either absent or contains only local bootstrap-planning artifacts that are not yet registered in the canonical spec index.

## Execution Dependencies
- none

## Target Subsystems
- `docs/specs/work_packets/tooltip_manager/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/tooltip_manager/**`

## Required Behavior
- Create or refresh `docs/specs/work_packets/tooltip_manager/`.
- Add `TOOLTIP_MANAGER_MANIFEST.md` and `TOOLTIP_MANAGER_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P03` using the current work-packet naming convention.
- Update `docs/specs/INDEX.md` with links to the `TOOLTIP_MANAGER` manifest and status ledger.
- Mark `P00` as `PASS` in `TOOLTIP_MANAGER_STATUS.md` and leave `P01` through `P03` as `PENDING`.
- Preserve the source-plan packet split: `P01` owns the persistent preference and manager contract, `P02` owns the menu action and existing tooltip-surface adoption, and `P03` owns the collision-avoidance dialog copy.
- Make no runtime, product-source, test, packaging-script, performance-doc, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `docs/specs/perf/**` or `docs/specs/requirements/**` in this packet.
- No implementation of `P01`, `P02`, or `P03` behavior in this packet.

## Verification Commands
1. `@'
from pathlib import Path

slugs = [
    "P00_bootstrap",
    "P01_tooltip_preference_and_manager_contract",
    "P02_view_menu_and_tooltip_surface_adoption",
    "P03_collision_avoidance_tooltip_copy",
]
required = [
    "docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_MANIFEST.md",
    "docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_STATUS.md",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "TOOLTIP_MANAGER Work Packet Manifest",
    "TOOLTIP_MANAGER Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("TOOLTIP_MANAGER_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -`

## Review Gate
- `@'
from pathlib import Path
text = Path("docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_STATUS.md").read_text(encoding="utf-8")
required = [
    "| P00 Bootstrap | `codex/tooltip-manager/p00-bootstrap` | PASS |",
    "| P01 Tooltip Preference and Manager Contract | `codex/tooltip-manager/p01-tooltip-preference-and-manager-contract` | PENDING |",
    "| P02 View Menu and Tooltip Surface Adoption | `codex/tooltip-manager/p02-view-menu-and-tooltip-surface-adoption` | PENDING |",
    "| P03 Collision-Avoidance Tooltip Copy | `codex/tooltip-manager/p03-collision-avoidance-tooltip-copy` | PENDING |",
]
for needle in required:
    if needle not in text:
        print("STATUS_MISSING: " + needle)
        raise SystemExit(1)
print("TOOLTIP_MANAGER_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -`

## Expected Artifacts
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_MANIFEST.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_STATUS.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P00_bootstrap.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P01_tooltip_preference_and_manager_contract.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P01_tooltip_preference_and_manager_contract_PROMPT.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P02_view_menu_and_tooltip_surface_adoption.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P02_view_menu_and_tooltip_surface_adoption_PROMPT.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P03_collision_avoidance_tooltip_copy.md`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P03_collision_avoidance_tooltip_copy_PROMPT.md`

## Acceptance Criteria
- The verification command returns `TOOLTIP_MANAGER_P00_FILE_GATE_PASS`.
- The review gate returns `TOOLTIP_MANAGER_P00_STATUS_PASS`.
- `TOOLTIP_MANAGER_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `docs/specs/INDEX.md` and the `tooltip_manager` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- Executor-created worktrees need these packet docs to exist on the target merge branch. If the bootstrap docs are still uncommitted, commit or merge them before starting implementation execution.
