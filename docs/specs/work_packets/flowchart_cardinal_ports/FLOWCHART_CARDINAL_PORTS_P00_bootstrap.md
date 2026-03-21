# FLOWCHART_CARDINAL_PORTS P00: Bootstrap

## Objective
- Establish the `FLOWCHART_CARDINAL_PORTS` packet set, initialize the status ledger, and register the packet docs in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `flowchart_cardinal_ports` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `docs/specs/work_packets/flowchart_cardinal_ports/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/**`

## Required Behavior
- Create `docs/specs/work_packets/flowchart_cardinal_ports/`.
- Add `FLOWCHART_CARDINAL_PORTS_MANIFEST.md` and `FLOWCHART_CARDINAL_PORTS_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P05` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `FLOWCHART_CARDINAL_PORTS` manifest and status ledger.
- Mark `P00` as `PASS` in `FLOWCHART_CARDINAL_PORTS_STATUS.md` and leave `P01` through `P05` as `PENDING`.
- Keep packet order, branch labels, sequential execution waves, locked defaults, review-gate structure, and wrap-up expectations aligned with the approved flowchart-cardinal-ports plan.
- Make no runtime, script, test, requirement-doc, or fixture changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to requirements, architecture docs, QA docs, fixtures, or `README.md` in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import subprocess

required = [
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_MANIFEST.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P00_bootstrap.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P01_neutral_port_contract.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P01_neutral_port_contract_PROMPT.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P02_cardinal_anchor_geometry.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P02_cardinal_anchor_geometry_PROMPT.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P03_canvas_neutral_interaction.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P03_canvas_neutral_interaction_PROMPT.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P04_flowchart_drop_connect_insert.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P04_flowchart_drop_connect_insert_PROMPT.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P05_regression_docs_traceability.md",
    "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P05_regression_docs_traceability_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
check = subprocess.run(
    ["git", "check-ignore", "docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_MANIFEST.md"],
    capture_output=True,
    text=True,
)
if check.returncode == 0:
    print("FLOWCHART_CARDINAL_PORTS_DOCS_IGNORED")
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "FLOWCHART_CARDINAL_PORTS Work Packet Manifest",
    "FLOWCHART_CARDINAL_PORTS Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("FLOWCHART_CARDINAL_PORTS_P00_FILE_GATE_PASS")
PY`

## Review Gate
- `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
text = Path("docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/flowchart-cardinal-ports/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("FLOWCHART_CARDINAL_PORTS_P00_STATUS_PASS")
PY`

## Expected Artifacts
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_MANIFEST.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P00_bootstrap.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P01_neutral_port_contract.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P01_neutral_port_contract_PROMPT.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P02_cardinal_anchor_geometry.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P02_cardinal_anchor_geometry_PROMPT.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P03_canvas_neutral_interaction.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P03_canvas_neutral_interaction_PROMPT.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P04_flowchart_drop_connect_insert.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P04_flowchart_drop_connect_insert_PROMPT.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P05_regression_docs_traceability.md`
- `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P05_regression_docs_traceability_PROMPT.md`

## Acceptance Criteria
- The first verification command returns `FLOWCHART_CARDINAL_PORTS_P00_FILE_GATE_PASS`.
- The review gate returns `FLOWCHART_CARDINAL_PORTS_P00_STATUS_PASS`.
- `FLOWCHART_CARDINAL_PORTS_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `docs/specs/INDEX.md` and the new `flowchart_cardinal_ports` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must start `P01`; this packet set is intentionally sequential.
