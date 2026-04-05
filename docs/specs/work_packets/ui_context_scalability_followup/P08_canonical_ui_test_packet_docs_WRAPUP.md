# P08 Canonical UI Test Packet Docs Wrap-Up

## Implementation Summary

- Packet: `P08`
- Branch Label: `codex/ui-context-scalability-followup/p08-canonical-ui-test-packet-docs`
- Commit Owner: `worker`
- Commit SHA: `5a1fde876a22e3f6664442aeac3dbfa234b1c06d`
- Changed Files: `ARCHITECTURE.md`, `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`, `docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md`, `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md`, `docs/specs/work_packets/ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md`, `docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md`, `docs/specs/work_packets/ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md`, `tests/test_context_budget_guardrails.py`, `tests/test_markdown_hygiene.py`, `docs/specs/work_packets/ui_context_scalability_followup/P08_canonical_ui_test_packet_docs_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/ui_context_scalability_followup/P08_canonical_ui_test_packet_docs_WRAPUP.md`, `docs/specs/work_packets/ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md`, `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md`, `docs/specs/work_packets/ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md`

- Updated the canonical UI packet entry path in `ARCHITECTURE.md`, `SUBSYSTEM_PACKET_INDEX.md`, and `FEATURE_PACKET_TEMPLATE.md` so future UI packets must name both an owning source subsystem packet and an owning regression packet before widening a packet-owned seam.
- Added canonical regression packet docs for main-window shell, graph-surface, and Track-B regressions inside the existing `ui_context_scalability_refactor` docs home, with stable entrypoints, shared support surfaces, source-packet links, and required test anchors.
- Ratcheted the follow-up context-budget caps from the P01 freeze values down to the steady-state thresholds established by P02 through P07, and updated the packet-owned guardrail and markdown hygiene tests so both the new docs and the new caps stay enforced automatically.

## Verification

- PASS: `.\venv\Scripts\python.exe scripts/check_context_budgets.py`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_context_budget_guardrails.py tests/test_markdown_hygiene.py tests/test_run_verification.py --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe scripts/check_markdown_links.py`
- PASS: review gate `.\venv\Scripts\python.exe scripts/check_markdown_links.py`
- Final Verification Verdict: PASS

## Manual Test Directives

1. Open `ARCHITECTURE.md`, follow the `UI subsystem packet index` link and then the `UI feature packet template` link, and confirm the entry path now requires both a source owner and a regression owner before editing a packet-owned UI seam.
2. Open `docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md` and confirm the new regression packet map points main-window shell, graph-surface, and Track-B work at the documented stable regression entrypoints and verification anchors.
3. Open `docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md` and confirm the metadata section now includes `Owning Source Subsystem Packet`, `Owning Regression Packet`, and `Inherited Secondary Regression Docs`.

## Residual Risks

- The new regression packet docs are now the canonical authoring surface for future UI work, so later packets must keep the source-to-regression mappings and required test anchors synchronized when stable entrypoints or support exports move.
- The machine checks cover line budgets, markdown structure, and link hygiene, but they do not verify that a future author picked the most appropriate regression owner for a cross-cutting change; that still depends on packet review discipline.

## Ready for Integration

- Yes: the canonical docs now require both owner types, the guardrail caps match the post-P07 steady state, the packet verification commands and review gate both passed, and the final diff stays inside the documented P08 write scope.
