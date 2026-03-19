Implement ARCH_FIFTH_PASS_P10_plugin_descriptor_package_contract.md exactly. Before editing, read ARCH_FIFTH_PASS_MANIFEST.md, ARCH_FIFTH_PASS_STATUS.md, and ARCH_FIFTH_PASS_P10_plugin_descriptor_package_contract.md. Implement only P10. Stay inside the packet write scope, preserve exact user-facing behavior, UI/UX, and performance, preserve current-schema `.sfe` behavior while treating pre-current-schema compatibility exactly as the packet specifies, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the packet wrap-up, update ARCH_FIFTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P10; do not start P11.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fifth-pass/p10-plugin-descriptor-package-contract`
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fifth_pass/P10_plugin_descriptor_package_contract_WRAPUP.md`
- Preserve legacy plugin loading as a compatibility fallback. This packet adds the descriptor path; it does not delete the old path.
