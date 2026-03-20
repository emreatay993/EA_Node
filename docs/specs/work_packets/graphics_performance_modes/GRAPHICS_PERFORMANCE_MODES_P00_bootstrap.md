# GRAPHICS_PERFORMANCE_MODES P00: Bootstrap

## Objective
- Establish the `GRAPHICS_PERFORMANCE_MODES` packet set, initialize the status ledger, and register the packet docs in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `graphics_performance_modes` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only for a narrow exception needed to make the new packet docs trackable
- `docs/specs/work_packets/graphics_performance_modes/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/graphics_performance_modes/**`

## Required Behavior
- Create `docs/specs/work_packets/graphics_performance_modes/`.
- Add `GRAPHICS_PERFORMANCE_MODES_MANIFEST.md` and `GRAPHICS_PERFORMANCE_MODES_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P10` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `GRAPHICS_PERFORMANCE_MODES` manifest and status ledger.
- Add the narrow `.gitignore` exception required so the new packet docs are not ignored by git.
- Mark `P00` as `PASS` in `GRAPHICS_PERFORMANCE_MODES_STATUS.md` and leave `P01` through `P10` as `PENDING`.
- Keep the packet order, branch labels, sequential execution waves, locked defaults, review-gate structure, and wrap-up expectations aligned with the approved Graphics Performance Modes V1 plan.
- Make no runtime, script, test, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to requirements, perf evidence docs, traceability docs, or `README.md` in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import subprocess

required = [
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_MANIFEST.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P00_bootstrap.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P01_preferences_runtime_contract.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P01_preferences_runtime_contract_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P02_graphics_settings_mode_ui.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P02_graphics_settings_mode_ui_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P03_status_strip_quick_toggle.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P03_status_strip_quick_toggle_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P04_canvas_performance_policy_foundation.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P04_canvas_performance_policy_foundation_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P05_max_performance_canvas_behavior.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P05_max_performance_canvas_behavior_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P06_node_render_quality_contract.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P06_node_render_quality_contract_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P07_host_surface_quality_seam.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P07_host_surface_quality_seam_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P08_media_surface_proxy_adoption.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P08_media_surface_proxy_adoption_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P09_perf_harness_modes_heavy_media.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P09_perf_harness_modes_heavy_media_PROMPT.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P10_docs_traceability.md",
    "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P10_docs_traceability_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
check = subprocess.run(
    ["git", "check-ignore", "docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_MANIFEST.md"],
    capture_output=True,
    text=True,
)
if check.returncode == 0:
    print("GRAPHICS_PERFORMANCE_MODES_DOCS_IGNORED")
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "GRAPHICS_PERFORMANCE_MODES Work Packet Manifest",
    "GRAPHICS_PERFORMANCE_MODES Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("GRAPHICS_PERFORMANCE_MODES_P00_FILE_GATE_PASS")
PY`

## Review Gate
- `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
text = Path("docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/graphics-performance-modes/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("GRAPHICS_PERFORMANCE_MODES_P00_STATUS_PASS")
PY`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_MANIFEST.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P00_bootstrap.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P01_preferences_runtime_contract.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P01_preferences_runtime_contract_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P02_graphics_settings_mode_ui.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P02_graphics_settings_mode_ui_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P03_status_strip_quick_toggle.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P03_status_strip_quick_toggle_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P04_canvas_performance_policy_foundation.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P04_canvas_performance_policy_foundation_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P05_max_performance_canvas_behavior.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P05_max_performance_canvas_behavior_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P06_node_render_quality_contract.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P06_node_render_quality_contract_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P07_host_surface_quality_seam.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P07_host_surface_quality_seam_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P08_media_surface_proxy_adoption.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P08_media_surface_proxy_adoption_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P09_perf_harness_modes_heavy_media.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P09_perf_harness_modes_heavy_media_PROMPT.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P10_docs_traceability.md`
- `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P10_docs_traceability_PROMPT.md`

## Acceptance Criteria
- The first verification command returns `GRAPHICS_PERFORMANCE_MODES_P00_FILE_GATE_PASS`.
- The review gate returns `GRAPHICS_PERFORMANCE_MODES_P00_STATUS_PASS`.
- `GRAPHICS_PERFORMANCE_MODES_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `graphics_performance_modes` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must start `P01`; this packet set is intentionally sequential.
