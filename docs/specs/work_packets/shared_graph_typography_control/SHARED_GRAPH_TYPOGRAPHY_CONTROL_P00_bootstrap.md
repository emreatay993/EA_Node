# SHARED_GRAPH_TYPOGRAPHY_CONTROL P00: Bootstrap

## Objective
- Establish the `SHARED_GRAPH_TYPOGRAPHY_CONTROL` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and bootstrap a strictly sequential fresh-context plan for the shared graph typography control defined in [PLANS_TO_IMPLEMENT/in_progress/typography.md](../../../../PLANS_TO_IMPLEMENT/in_progress/typography.md) while explicitly retaining [PLANS_TO_IMPLEMENT/completed/Persistent_Node_Elapsed_Times.md](../../../../PLANS_TO_IMPLEMENT/completed/Persistent_Node_Elapsed_Times.md) as a dependent planning precedent.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- `docs/specs/work_packets/shared_graph_typography_control/` is either absent or contains only local bootstrap-planning artifacts that are not yet registered in the canonical spec index.

## Execution Dependencies
- none

## Target Subsystems
- `docs/specs/work_packets/shared_graph_typography_control/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/shared_graph_typography_control/**`

## Required Behavior
- Create or refresh `docs/specs/work_packets/shared_graph_typography_control/`.
- Add `SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md` and `SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P07` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `SHARED_GRAPH_TYPOGRAPHY_CONTROL` manifest and status ledger.
- Mark `P00` as `PASS` in `SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md` and leave `P01` through `P07` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, retained QA-matrix closeout, and the dependent elapsed-footer precedent aligned with [PLANS_TO_IMPLEMENT/in_progress/typography.md](../../../../PLANS_TO_IMPLEMENT/in_progress/typography.md) and [PLANS_TO_IMPLEMENT/completed/Persistent_Node_Elapsed_Times.md](../../../../PLANS_TO_IMPLEMENT/completed/Persistent_Node_Elapsed_Times.md).
- Make no runtime, product-source, test, packaging-script, or requirement-doc changes outside the documentation bootstrap scope.

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
    "P01_preferences_typography_schema_normalization",
    "P02_shell_typography_projection",
    "P03_canvas_typography_contract_and_metrics",
    "P04_standard_node_chrome_typography_adoption",
    "P05_inline_and_edge_typography_adoption",
    "P06_graphics_settings_typography_control",
    "P07_verification_docs_traceability_closeout",
]
required = [
    "docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md",
    "docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "SHARED_GRAPH_TYPOGRAPHY_CONTROL Work Packet Manifest",
    "SHARED_GRAPH_TYPOGRAPHY_CONTROL Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -`

## Review Gate
- `@'
from pathlib import Path
text = Path("docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/shared-graph-typography-control/p00-bootstrap` | PASS | `aa939b6c922a19e10bd32a7c8e0bcf090dec3fb0` |" not in text:
    raise SystemExit(1)
print("SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -`

## Expected Artifacts
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_bootstrap.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P01_preferences_typography_schema_normalization.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P01_preferences_typography_schema_normalization_PROMPT.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P02_shell_typography_projection.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P02_shell_typography_projection_PROMPT.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P03_canvas_typography_contract_and_metrics.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P03_canvas_typography_contract_and_metrics_PROMPT.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_standard_node_chrome_typography_adoption.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_standard_node_chrome_typography_adoption_PROMPT.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_inline_and_edge_typography_adoption.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_inline_and_edge_typography_adoption_PROMPT.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P06_graphics_settings_typography_control.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P06_graphics_settings_typography_control_PROMPT.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P07_verification_docs_traceability_closeout.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P07_verification_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_FILE_GATE_PASS`.
- The review gate returns `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_STATUS_PASS`.
- `SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `docs/specs/INDEX.md` and the `shared_graph_typography_control` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
