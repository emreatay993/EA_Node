# PERSISTENT_NODE_ELAPSED_TIMES P00: Bootstrap

## Objective
- Establish the `PERSISTENT_NODE_ELAPSED_TIMES` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and bootstrap a sequential follow-up plan for persistent elapsed timing on top of the shipped node-execution visualization path.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- `docs/specs/work_packets/persistent_node_elapsed_times/` is either absent or contains only local bootstrap-planning artifacts that are not yet registered in the canonical spec index.

## Execution Dependencies
- none

## Target Subsystems
- `docs/specs/work_packets/persistent_node_elapsed_times/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/**`

## Required Behavior
- Create or refresh `docs/specs/work_packets/persistent_node_elapsed_times/`.
- Add `PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md` and `PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P06` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `PERSISTENT_NODE_ELAPSED_TIMES` manifest and status ledger.
- Mark `P00` as `PASS` in `PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md` and leave `P01` through `P06` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and retained QA-matrix reuse aligned with [PLANS_TO_IMPLEMENT/in_progress/Persistent_Node_Elapsed_Times.md](../../../../PLANS_TO_IMPLEMENT/in_progress/Persistent_Node_Elapsed_Times.md).
- Make no runtime, product-source, test, packaging-script, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md` or `docs/specs/requirements/**` in this packet.

## Verification Commands
1. `@'
from pathlib import Path

slugs = [
    "P00_bootstrap",
    "P01_worker_timing_protocol_projection",
    "P02_shell_elapsed_cache_projection",
    "P03_graph_canvas_elapsed_bindings",
    "P04_history_action_type_expansion",
    "P05_timing_cache_invalidation_hooks",
    "P06_node_footer_persistent_elapsed_rendering",
    "P07_verification_docs_traceability_closeout",
]
required = [
    "docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md",
    "docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "PERSISTENT_NODE_ELAPSED_TIMES Work Packet Manifest",
    "PERSISTENT_NODE_ELAPSED_TIMES Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("PERSISTENT_NODE_ELAPSED_TIMES_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -`

## Review Gate
- `@'
from pathlib import Path
text = Path("docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/persistent-node-elapsed-times/p00-bootstrap` | PASS | `LOCAL_ONLY_NOT_COMMITTED` |" not in text:
    raise SystemExit(1)
print("PERSISTENT_NODE_ELAPSED_TIMES_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -`

## Expected Artifacts
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P00_bootstrap.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P01_worker_timing_protocol_projection.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P01_worker_timing_protocol_projection_PROMPT.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P02_shell_elapsed_cache_projection.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P02_shell_elapsed_cache_projection_PROMPT.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P03_graph_canvas_elapsed_bindings.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P03_graph_canvas_elapsed_bindings_PROMPT.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P04_history_action_type_expansion.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P04_history_action_type_expansion_PROMPT.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P05_timing_cache_invalidation_hooks.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P05_timing_cache_invalidation_hooks_PROMPT.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P06_node_footer_persistent_elapsed_rendering.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P06_node_footer_persistent_elapsed_rendering_PROMPT.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P07_verification_docs_traceability_closeout.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P07_verification_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `PERSISTENT_NODE_ELAPSED_TIMES_P00_FILE_GATE_PASS`.
- The review gate returns `PERSISTENT_NODE_ELAPSED_TIMES_P00_STATUS_PASS`.
- `PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `docs/specs/INDEX.md` and the `persistent_node_elapsed_times` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
