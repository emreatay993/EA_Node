# V1_CLASSIC_EXPLORER_FOLDER_NODE P00: Bootstrap

## Objective
- Establish the `V1_CLASSIC_EXPLORER_FOLDER_NODE` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and define the fresh-context execution plan for the V1 Classic Explorer folder node.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- `docs/specs/work_packets/v1_classic_explorer_folder_node/` is absent or contains only local bootstrap-planning artifacts.

## Execution Dependencies
- none

## Target Subsystems
- `docs/specs/work_packets/v1_classic_explorer_folder_node/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/**`

## Required Behavior
- Create or refresh `docs/specs/work_packets/v1_classic_explorer_folder_node/`.
- Add `V1_CLASSIC_EXPLORER_FOLDER_NODE_MANIFEST.md` and `V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P07` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `V1_CLASSIC_EXPLORER_FOLDER_NODE` manifest and status ledger.
- Mark `P00` as `PASS` in `V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md` and leave `P01` through `P07` as `PENDING`.
- Preserve the locked defaults from the manifest: real filesystem browsing, confirmed mutations, passive node runtime behavior, transient UI state outside `.sfe`, and graph mutation through existing services.
- Make no runtime, product-source, test, packaging-script, performance-doc, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `docs/specs/perf/**` or `docs/specs/requirements/**` in this packet.
- No execution of `P01` or later implementation packets.

## Verification Commands
1. `@'
from pathlib import Path

root = Path("docs/specs/work_packets/v1_classic_explorer_folder_node")
slugs = [
    "P00_bootstrap",
    "P01_node_contract",
    "P02_filesystem_service",
    "P03_bridge_actions",
    "P04_qml_surface",
    "P05_shell_inspector_library",
    "P06_integration_tests",
    "P07_closeout_verification",
]
required = [
    root / "V1_CLASSIC_EXPLORER_FOLDER_NODE_MANIFEST.md",
    root / "V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md",
]
for slug in slugs:
    required.append(root / f"V1_CLASSIC_EXPLORER_FOLDER_NODE_{slug}.md")
    required.append(root / f"V1_CLASSIC_EXPLORER_FOLDER_NODE_{slug}_PROMPT.md")
missing = [str(path) for path in required if not path.exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "V1_CLASSIC_EXPLORER_FOLDER_NODE Work Packet Manifest",
    "V1_CLASSIC_EXPLORER_FOLDER_NODE Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -`

## Review Gate
- `@'
from pathlib import Path
text = Path("docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md").read_text(encoding="utf-8")
required = [
    "| P00 Bootstrap | `codex/v1-classic-explorer-folder-node/p00-bootstrap` | PASS |",
    "| P01 Node Contract | `codex/v1-classic-explorer-folder-node/p01-node-contract` | PENDING |",
    "| P02 Filesystem Service | `codex/v1-classic-explorer-folder-node/p02-filesystem-service` | PENDING |",
    "| P03 Bridge Actions | `codex/v1-classic-explorer-folder-node/p03-bridge-actions` | PENDING |",
    "| P04 QML Surface | `codex/v1-classic-explorer-folder-node/p04-qml-surface` | PENDING |",
    "| P05 Shell Inspector Library | `codex/v1-classic-explorer-folder-node/p05-shell-inspector-library` | PENDING |",
    "| P06 Integration Tests | `codex/v1-classic-explorer-folder-node/p06-integration-tests` | PENDING |",
    "| P07 Closeout Verification | `codex/v1-classic-explorer-folder-node/p07-closeout-verification` | PENDING |",
]
for needle in required:
    if needle not in text:
        print("STATUS_MISSING: " + needle)
        raise SystemExit(1)
print("V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -`

## Expected Artifacts
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_MANIFEST.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_bootstrap.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P01_node_contract.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P01_node_contract_PROMPT.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P02_filesystem_service.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P02_filesystem_service_PROMPT.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P03_bridge_actions.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P03_bridge_actions_PROMPT.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P04_qml_surface.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P04_qml_surface_PROMPT.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P05_shell_inspector_library.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P05_shell_inspector_library_PROMPT.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P06_integration_tests.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P06_integration_tests_PROMPT.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P07_closeout_verification.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_P07_closeout_verification_PROMPT.md`

## Acceptance Criteria
- The verification command returns `V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_FILE_GATE_PASS`.
- The review gate returns `V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_STATUS_PASS`.
- `V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths for this packet are `docs/specs/INDEX.md` and the `v1_classic_explorer_folder_node` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- Executor-created worktrees need these packet docs to exist on the target merge branch. If the bootstrap docs are still uncommitted, commit or merge them before starting implementation execution.
