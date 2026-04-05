# UI_CONTEXT_SCALABILITY_FOLLOWUP P01: Guardrail Catalog Expansion

## Objective

- Extend the existing machine-enforced UI context-budget catalog to the remaining oversized source and regression hotspots and wire that check into the normal fast verification path.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet is in progress.

## Execution Dependencies

- `P00`

## Target Subsystems

- `scripts/check_context_budgets.py`
- `scripts/run_verification.py`
- `scripts/verification_manifest.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`
- `tests/test_context_budget_guardrails.py`
- `tests/test_run_verification.py`

## Conservative Write Scope

- `scripts/check_context_budgets.py`
- `scripts/run_verification.py`
- `scripts/verification_manifest.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`
- `tests/test_context_budget_guardrails.py`
- `tests/test_run_verification.py`
- `docs/specs/work_packets/ui_context_scalability_followup/P01_guardrail_catalog_expansion_WRAPUP.md`

## Required Behavior

- Add explicit machine-checked context-budget rules for at least these currently unguarded hotspots:
  - `ea_node_editor/ui/shell/window_state_helpers.py`
  - `ea_node_editor/ui/shell/controllers/project_session_services.py`
  - `ea_node_editor/ui_qml/graph_surface_metrics.py`
  - `ea_node_editor/ui_qml/edge_routing.py`
  - `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
  - `tests/main_window_shell/bridge_contracts.py`
  - `tests/test_passive_graph_surface_host.py`
  - `tests/test_graph_surface_input_contract.py`
  - `tests/graph_track_b/qml_preference_bindings.py`
  - `tests/graph_track_b/scene_and_model.py`
- Use this packet to freeze the current hotspot catalog with explicit owner labels and initial caps rather than leaving them unguarded until later packets land.
- Wire the context-budget check into the normal fast verification path so developers see the failure in the standard entry workflow instead of only in a one-off manual command.
- Update packet-owned tests and verification metadata so the new guardrails and the fast-mode integration are asserted automatically.
- Do not change product behavior or begin the actual source or regression splits in this packet.

## Non-Goals

- No packet-owned runtime refactors yet.
- No packet-owned regression-suite splits yet.
- No canonical packet-doc rewrite yet; that belongs to `P08`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe scripts/check_context_budgets.py
.\venv\Scripts\python.exe -m pytest tests/test_context_budget_guardrails.py tests/test_run_verification.py --ignore=venv -q
.\venv\Scripts\python.exe scripts/run_verification.py --mode fast --dry-run
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_context_budgets.py
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_followup/P01_guardrail_catalog_expansion_WRAPUP.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`
- `scripts/check_context_budgets.py`
- `scripts/run_verification.py`

## Acceptance Criteria

- The remaining oversized source and regression hotspots are explicitly guarded in the canonical rules file.
- The context-budget check is part of the normal fast verification entry path.
- The packet-owned tests and metadata that describe the guardrails pass.

## Handoff Notes

- `P02` through `P07` spend down the frozen hotspots. `P08` is responsible for ratcheting the initial caps to their final steady-state targets once the splits are done.
