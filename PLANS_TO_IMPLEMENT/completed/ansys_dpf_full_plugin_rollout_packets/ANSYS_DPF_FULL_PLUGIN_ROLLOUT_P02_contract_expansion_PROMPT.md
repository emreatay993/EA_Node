Implement ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P02_contract_expansion.md exactly. Before editing, read ANSYS_DPF_FULL_PLUGIN_ROLLOUT_MANIFEST.md, ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md, and ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P02_contract_expansion.md. Implement only P02. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P02_contract_expansion_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/ansys-dpf-full-plugin-rollout/p02-contract-expansion`.
- Keep existing non-DPF node contracts working while widening the DPF metadata surface.
