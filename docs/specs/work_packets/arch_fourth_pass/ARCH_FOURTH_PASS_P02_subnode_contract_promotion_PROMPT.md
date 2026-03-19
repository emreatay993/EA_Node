Implement ARCH_FOURTH_PASS_P02_subnode_contract_promotion.md exactly. Before editing, read ARCH_FOURTH_PASS_MANIFEST.md, ARCH_FOURTH_PASS_STATUS.md, and ARCH_FOURTH_PASS_P02_subnode_contract_promotion.md. Implement only P02. Stay inside the packet write scope, preserve public subnode type ids and runtime behavior unless the packet explicitly changes an internal ownership seam, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_fourth_pass/P02_subnode_contract_promotion_WRAPUP.md`, update ARCH_FOURTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fourth-pass/p02-subnode-contract-promotion`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_worker -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fourth_pass/P02_subnode_contract_promotion_WRAPUP.md`
- Keep this packet focused on ownership and dependency direction. Do not widen into graph mutation-service or shell/UI refactors.
