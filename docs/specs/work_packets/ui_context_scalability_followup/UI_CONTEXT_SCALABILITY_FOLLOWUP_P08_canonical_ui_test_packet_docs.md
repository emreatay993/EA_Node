# UI_CONTEXT_SCALABILITY_FOLLOWUP P08: Canonical UI Test Packet Docs

## Objective

- Update the canonical UI packet docs so future work names both a source subsystem owner and a regression owner, and ratchet the follow-up guardrail caps to their steady-state thresholds.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet is in progress.

## Execution Dependencies

- `P07`

## Target Subsystems

- `ARCHITECTURE.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`
- `docs/specs/work_packets/ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md`
- `tests/test_context_budget_guardrails.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_run_verification.py`

## Conservative Write Scope

- `ARCHITECTURE.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`
- `docs/specs/work_packets/ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md`
- `tests/test_context_budget_guardrails.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_run_verification.py`
- `docs/specs/work_packets/ui_context_scalability_followup/P08_canonical_ui_test_packet_docs_WRAPUP.md`

## Required Behavior

- Update `SUBSYSTEM_PACKET_INDEX.md` so future UI work references both the existing source-side packet docs and the new regression-side packet docs.
- Update `FEATURE_PACKET_TEMPLATE.md` so future UI packets must name both an owning source subsystem packet and an owning regression packet.
- Add these canonical regression packet docs under the existing `ui_context_scalability_refactor` docs home:
  - `MAIN_WINDOW_SHELL_TEST_PACKET.md`
  - `GRAPH_SURFACE_TEST_PACKET.md`
  - `TRACK_B_TEST_PACKET.md`
- Update `ARCHITECTURE.md` so engineers are pointed at the canonical UI source-plus-regression packet docs before editing packet-owned UI seams.
- Ratchet the follow-up guardrail caps in `CONTEXT_BUDGET_RULES.json` from the baseline-freeze values introduced by `P01` to the steady-state targets established by `P02` through `P07`.
- Update packet-owned docs and tests so the canonical packet-doc guidance and the ratcheted caps are asserted automatically.

## Non-Goals

- No further source or regression refactors.
- No QA-matrix or traceability closeout yet; that belongs to `P09`.
- No second canonical UI packet-doc home outside `ui_context_scalability_refactor`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe scripts/check_context_budgets.py
.\venv\Scripts\python.exe -m pytest tests/test_context_budget_guardrails.py tests/test_markdown_hygiene.py tests/test_run_verification.py --ignore=venv -q
.\venv\Scripts\python.exe scripts/check_markdown_links.py
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_markdown_links.py
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_followup/P08_canonical_ui_test_packet_docs_WRAPUP.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md`

## Acceptance Criteria

- Future UI packet authoring requires both a source owner and a regression owner.
- The canonical packet docs for those owners live in the existing `ui_context_scalability_refactor` docs home.
- The follow-up guardrail caps are ratcheted to their steady-state targets.
- Packet-owned markdown and guardrail checks pass.

## Handoff Notes

- `P09` closes the packet set by publishing the QA and traceability audit that points at the expanded packet docs and ratcheted guardrails.
