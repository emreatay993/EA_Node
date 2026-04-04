# UI_CONTEXT_SCALABILITY_REFACTOR P07: Context Budget Guardrails

## Objective

- Add machine-enforced context budgets and hotspot ownership rules so future UI work cannot silently grow the same umbrella files back into context sinks.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_REFACTOR` packet is in progress.

## Execution Dependencies

- `P06`

## Target Subsystems

- `scripts/check_context_budgets.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`
- `tests/test_context_budget_guardrails.py`
- `tests/test_dead_code_hygiene.py`
- `scripts/verification_manifest.py`
- `tests/test_run_verification.py`

## Conservative Write Scope

- `scripts/check_context_budgets.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`
- `tests/test_context_budget_guardrails.py`
- `tests/test_dead_code_hygiene.py`
- `scripts/verification_manifest.py`
- `tests/test_run_verification.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P07_context_budget_guardrails_WRAPUP.md`

## Required Behavior

- Add `scripts/check_context_budgets.py` as the packet-owned machine check for UI hotspot budgets.
- Add `CONTEXT_BUDGET_RULES.json` as the canonical ruleset for guarded files, allowed caps, and ownership labels.
- Guard at least these packet-owned hotspots: `window.py`, `presenters/__init__.py`, the presenter implementation modules, `graph_scene_bridge.py`, `GraphCanvas.qml`, `EdgeLayer.qml`, `viewer_session_bridge.py`, `viewer_session_service.py`, and `GraphViewerSurface.qml`.
- Encode the post-refactor hard caps established by earlier packets instead of a single global cap.
- Add targeted automated proof through `tests/test_context_budget_guardrails.py`, and wire the guardrail command into packet-owned verification metadata.
- Do not rely only on prose docs for enforcement.

## Non-Goals

- No further product behavior changes.
- No broad architecture-doc rewrite yet; that belongs to `P08` and `P09`.
- No repo-wide size policing outside the packet-owned UI hotspots.

## Verification Commands

```powershell
.\venv\Scripts\python.exe scripts/check_context_budgets.py
.\venv\Scripts\python.exe -m pytest tests/test_context_budget_guardrails.py tests/test_run_verification.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_context_budgets.py
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_refactor/P07_context_budget_guardrails_WRAPUP.md`
- `scripts/check_context_budgets.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`
- `tests/test_context_budget_guardrails.py`

## Acceptance Criteria

- The packet-owned UI hotspot budgets are machine-checked.
- The ruleset names the guarded files and their post-refactor hard caps explicitly.
- The guardrail script and targeted tests pass.

## Handoff Notes

- `P08` should publish subsystem packet docs that point engineers at these guardrails instead of repeating the rules in every feature thread.
