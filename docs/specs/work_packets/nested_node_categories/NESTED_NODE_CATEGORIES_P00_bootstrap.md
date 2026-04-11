# NESTED_NODE_CATEGORIES P00: Bootstrap

## Objective
- Establish the `NESTED_NODE_CATEGORIES` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and bootstrap a strictly sequential fresh-context plan for the 10-level nested node category rollout defined in [PLANS_TO_IMPLEMENT/in_progress/nested_node_categories.md](../../../../PLANS_TO_IMPLEMENT/in_progress/nested_node_categories.md).

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- `docs/specs/work_packets/nested_node_categories/` is either absent or contains only local bootstrap-planning artifacts that are not yet registered in the canonical spec index.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/nested_node_categories/*`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/nested_node_categories/**`

## Required Behavior
- Create or refresh `docs/specs/work_packets/nested_node_categories/`.
- Add `NESTED_NODE_CATEGORIES_MANIFEST.md` and `NESTED_NODE_CATEGORIES_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P05` using the canonical naming convention.
- Update `.gitignore` so the new packet docs and final QA matrix can be tracked inside the otherwise ignored spec-pack directories.
- Update `docs/specs/INDEX.md` with links to the `NESTED_NODE_CATEGORIES` manifest and status ledger.
- Mark `P00` as `PASS` in `NESTED_NODE_CATEGORIES_STATUS.md` and leave `P01` through `P05` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, retained QA-matrix closeout, and the DPF/library/QML migration boundaries aligned with [PLANS_TO_IMPLEMENT/in_progress/nested_node_categories.md](../../../../PLANS_TO_IMPLEMENT/in_progress/nested_node_categories.md).
- Make no runtime, product-source, test, packaging-script, or requirement-doc changes outside the bootstrap scope.

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
    "P01_sdk_category_path_contract",
    "P02_registry_path_filters_and_dpf_taxonomy",
    "P03_library_tree_payload_projection",
    "P04_qml_nested_library_presentation",
    "P05_verification_docs_traceability_closeout",
]
required = [
    ".gitignore",
    "docs/specs/INDEX.md",
    "docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_MANIFEST.md",
    "docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_STATUS.md",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "NESTED_NODE_CATEGORIES Work Packet Manifest",
    "NESTED_NODE_CATEGORIES Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
gitignore_text = Path(".gitignore").read_text(encoding="utf-8")
for needle in (
    "!docs/specs/work_packets/nested_node_categories/",
    "!docs/specs/perf/NESTED_NODE_CATEGORIES_QA_MATRIX.md",
):
    if needle not in gitignore_text:
        print("GITIGNORE_MISSING: " + needle)
        raise SystemExit(1)
print("NESTED_NODE_CATEGORIES_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -`

## Review Gate
- `@'
from pathlib import Path

text = Path("docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_STATUS.md").read_text(encoding="utf-8")
required_rows = (
    "| P00 Bootstrap | `codex/nested-node-categories/p00-bootstrap` | PASS |",
    "| P01 SDK Category Path Contract | `codex/nested-node-categories/p01-sdk-category-path-contract` | PENDING |",
    "| P02 Registry Path Filters and DPF Taxonomy | `codex/nested-node-categories/p02-registry-path-filters-and-dpf-taxonomy` | PENDING |",
    "| P03 Library Tree Payload Projection | `codex/nested-node-categories/p03-library-tree-payload-projection` | PENDING |",
    "| P04 QML Nested Library Presentation | `codex/nested-node-categories/p04-qml-nested-library-presentation` | PENDING |",
    "| P05 Verification Docs Traceability Closeout | `codex/nested-node-categories/p05-verification-docs-traceability-closeout` | PENDING |",
)
for row in required_rows:
    if row not in text:
        raise SystemExit(1)
print("NESTED_NODE_CATEGORIES_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -`

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_MANIFEST.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_STATUS.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P00_bootstrap.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P01_sdk_category_path_contract.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P01_sdk_category_path_contract_PROMPT.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P02_registry_path_filters_and_dpf_taxonomy.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P02_registry_path_filters_and_dpf_taxonomy_PROMPT.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P03_library_tree_payload_projection.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P03_library_tree_payload_projection_PROMPT.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P04_qml_nested_library_presentation.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P04_qml_nested_library_presentation_PROMPT.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P05_verification_docs_traceability_closeout.md`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_P05_verification_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `NESTED_NODE_CATEGORIES_P00_FILE_GATE_PASS`.
- The review gate returns `NESTED_NODE_CATEGORIES_P00_STATUS_PASS`.
- `NESTED_NODE_CATEGORIES_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the `nested_node_categories` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- Because the executor creates packet worktrees from the target merge branch, commit these bootstrap docs onto that branch before trying to execute `P01` in a fresh orchestrator thread.
