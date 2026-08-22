Implement ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P06_runtime_persistence_portability.md exactly. Before editing, read ANSYS_DPF_FULL_PLUGIN_ROLLOUT_MANIFEST.md, ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md, and ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P06_runtime_persistence_portability.md. Implement only P06. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P06; do not start P07.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P06_runtime_persistence_portability_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/ansys-dpf-full-plugin-rollout/p06-runtime-persistence-portability`.
- Preserve saved labels, properties, exposed-port state, and edges when DPF is unavailable on reopen.
