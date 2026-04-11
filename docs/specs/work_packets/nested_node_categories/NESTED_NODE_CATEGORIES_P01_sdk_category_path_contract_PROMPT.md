Implement NESTED_NODE_CATEGORIES_P01_sdk_category_path_contract.md exactly. Before editing, read NESTED_NODE_CATEGORIES_MANIFEST.md, NESTED_NODE_CATEGORIES_STATUS.md, and NESTED_NODE_CATEGORIES_P01_sdk_category_path_contract.md. Implement only P01. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update NESTED_NODE_CATEGORIES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- If the wrap-up lands in a follow-up docs commit, the recorded accepted SHA may still point to the earlier substantive packet commit as long as it remains reachable from the packet branch and the wrap-up `Changed Files` list reflects the full packet-branch diff.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/nested-node-categories/p01-sdk-category-path-contract`.
- Review Gate: `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py -k nested_category_sdk --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/nested_node_categories/P01_sdk_category_path_contract_WRAPUP.md`
- Keep this packet focused on the SDK contract, validation, helpers, and in-repo authoring migration. Do not begin the real DPF nesting, library trie rewrite, or QML collapse work here.
