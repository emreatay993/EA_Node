## Implementation Summary
- Packet: `P07`
- Branch Label: `codex/ui-context-scalability-refactor/p07-context-budget-guardrails`
- Commit Owner: `worker`
- Commit SHA: `5537558c7d64539e51084455a6d0f44643373871`
- Changed Files: `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`, `docs/specs/work_packets/ui_context_scalability_refactor/P07_context_budget_guardrails_WRAPUP.md`, `scripts/check_context_budgets.py`, `scripts/verification_manifest.py`, `tests/test_context_budget_guardrails.py`, `tests/test_dead_code_hygiene.py`, `tests/test_run_verification.py`
- Artifacts Produced: `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`, `docs/specs/work_packets/ui_context_scalability_refactor/P07_context_budget_guardrails_WRAPUP.md`, `scripts/check_context_budgets.py`, `scripts/verification_manifest.py`, `tests/test_context_budget_guardrails.py`, `tests/test_dead_code_hygiene.py`, `tests/test_run_verification.py`

Added a packet-owned JSON ruleset that explicitly records the inherited hard caps and owner labels for the guarded UI hotspot files from `P01` through `P06`, and added `scripts/check_context_budgets.py` as the machine check that fails on missing guarded files, malformed rules, or line-budget overruns.

Wired the new guardrail command into `scripts/verification_manifest.py`, added targeted proof in `tests/test_context_budget_guardrails.py`, and extended packet-owned regression coverage in `tests/test_run_verification.py` and `tests/test_dead_code_hygiene.py` so the budget catalog, verification metadata, and retired umbrella-support files stay enforced by code rather than prose alone.

## Verification
- PASS: `.\venv\Scripts\python.exe scripts/check_context_budgets.py`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_context_budget_guardrails.py tests/test_run_verification.py --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe scripts/check_context_budgets.py`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives
Ready for manual testing
- Prerequisite: stay in `C:\w\ea-node-editor-ui-context-p07` and use the project venv so the packet-owned checker runs against the intended worktree state.
- Baseline smoke: run `.\venv\Scripts\python.exe scripts/check_context_budgets.py`. Expected result: the command prints `PASS: context budget guardrails satisfied for 13 guarded hotspots.` and exits cleanly.
- Verification metadata smoke: run `.\venv\Scripts\python.exe -m pytest tests/test_context_budget_guardrails.py tests/test_run_verification.py --ignore=venv -q`. Expected result: the suite passes and confirms the ruleset, checker, and verification-manifest wiring all match the packet contract.
- Failure-path smoke: temporarily lower one cap in `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json` below the current file size of a guarded hotspot, rerun `.\venv\Scripts\python.exe scripts/check_context_budgets.py`, then restore the JSON. Expected result: the checker fails with the owning packet label, guarded path, actual line count, and configured cap for the violated hotspot.

## Residual Risks
- The guardrails are intentionally limited to the packet-owned hotspot list from `P01` through `P06`, so future umbrella-risk files outside this catalog will still require explicit rule entries rather than automatic repo-wide policing.

## Ready for Integration
- Yes: the packet-owned ruleset, checker, and verification metadata are committed on the correct packet branch, the exact P07 verification commands passed, and the review-gate command passed on the accepted substantive state.
