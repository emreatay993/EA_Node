Implement PLUGIN_PACKAGE_CONTRACT_P03_package_export_contract.md exactly. Before editing, read PLUGIN_PACKAGE_CONTRACT_MANIFEST.md, PLUGIN_PACKAGE_CONTRACT_STATUS.md, and PLUGIN_PACKAGE_CONTRACT_P03_package_export_contract.md. Implement only P03. Stay inside the packet write scope, preserve raw single-file plugin drop-ins, entry-point plugin loading, and current type_id behavior unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/plugin_package_contract/P03_package_export_contract_WRAPUP.md`, update PLUGIN_PACKAGE_CONTRACT_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/plugin-package-contract/p03-package-export-contract`.
- Review Gate: `./venv/Scripts/python.exe -m pytest -n auto tests/test_package_manager.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/plugin_package_contract/P03_package_export_contract_WRAPUP.md`
- Keep this packet at the lower-level export contract. Do not widen into File-menu dialogs or controller messaging here.
