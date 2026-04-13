# TITLE_ICONS_FOR_NON_PASSIVE_NODES P00: Bootstrap

## Objective
- Establish the `TITLE_ICONS_FOR_NON_PASSIVE_NODES` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and bootstrap a fresh-context plan for path-based title-leading icons defined in [PLANS_TO_IMPLEMENT/in_progress/title_icons_for_non_passive_nodes.md](../../../../PLANS_TO_IMPLEMENT/in_progress/title_icons_for_non_passive_nodes.md).

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/` is either absent or contains only local bootstrap-planning artifacts that are not yet registered in the canonical spec index.

## Execution Dependencies
- none

## Target Subsystems
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/**`

## Required Behavior
- Create or refresh `docs/specs/work_packets/title_icons_for_non_passive_nodes/`.
- Add `TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md` and `TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P05` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `TITLE_ICONS_FOR_NON_PASSIVE_NODES` manifest and status ledger.
- Mark `P00` as `PASS` in `TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md` and leave `P01` through `P05` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review gates, retained QA-matrix closeout, and the shared-typography precedent aligned with [PLANS_TO_IMPLEMENT/in_progress/title_icons_for_non_passive_nodes.md](../../../../PLANS_TO_IMPLEMENT/in_progress/title_icons_for_non_passive_nodes.md).
- Make no runtime, product-source, test, packaging-script, performance-doc, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `docs/specs/perf/**` or `docs/specs/requirements/**` in this packet.

## Verification Commands
1. `@'
from pathlib import Path

slugs = [
    "P00_bootstrap",
    "P01_path_resolver_and_payload_contract",
    "P02_icon_size_preferences_and_bridge",
    "P03_qml_header_icon_rendering",
    "P04_builtin_node_icon_assets_and_migration",
    "P05_verification_docs_traceability_closeout",
]
required = [
    "docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md",
    "docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "TITLE_ICONS_FOR_NON_PASSIVE_NODES Work Packet Manifest",
    "TITLE_ICONS_FOR_NON_PASSIVE_NODES Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -`

## Review Gate
- `@'
from pathlib import Path
text = Path("docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md").read_text(encoding="utf-8")
required = [
    "| P00 Bootstrap | `codex/title-icons-for-non-passive-nodes/p00-bootstrap` | PASS |",
    "| P01 Path Resolver and Payload Contract | `codex/title-icons-for-non-passive-nodes/p01-path-resolver-and-payload-contract` | PENDING |",
    "| P02 Icon Size Preferences and Bridge | `codex/title-icons-for-non-passive-nodes/p02-icon-size-preferences-and-bridge` | PENDING |",
    "| P03 QML Header Icon Rendering | `codex/title-icons-for-non-passive-nodes/p03-qml-header-icon-rendering` | PENDING |",
    "| P04 Built-In Node Icon Assets and Migration | `codex/title-icons-for-non-passive-nodes/p04-builtin-node-icon-assets-and-migration` | PENDING |",
    "| P05 Verification Docs Traceability Closeout | `codex/title-icons-for-non-passive-nodes/p05-verification-docs-traceability-closeout` | PENDING |",
]
for needle in required:
    if needle not in text:
        print("STATUS_MISSING: " + needle)
        raise SystemExit(1)
print("TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -`

## Expected Artifacts
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_bootstrap.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P01_path_resolver_and_payload_contract.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P01_path_resolver_and_payload_contract_PROMPT.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P02_icon_size_preferences_and_bridge.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P02_icon_size_preferences_and_bridge_PROMPT.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P03_qml_header_icon_rendering.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P03_qml_header_icon_rendering_PROMPT.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P04_builtin_node_icon_assets_and_migration.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P04_builtin_node_icon_assets_and_migration_PROMPT.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P05_verification_docs_traceability_closeout.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_P05_verification_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_FILE_GATE_PASS`.
- The review gate returns `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_STATUS_PASS`.
- `TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `docs/specs/INDEX.md` and the `title_icons_for_non_passive_nodes` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- Executor-created worktrees need these packet docs to exist on the target merge branch. If the bootstrap docs are still uncommitted, commit or merge them before starting implementation execution.
