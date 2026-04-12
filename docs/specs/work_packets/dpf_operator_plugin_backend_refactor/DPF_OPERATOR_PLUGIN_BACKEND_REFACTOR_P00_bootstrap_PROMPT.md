Implement DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P00_bootstrap.md exactly. Before editing, read DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_MANIFEST.md, DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md, and DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/dpf-operator-plugin-backend-refactor/p00-bootstrap`.
- Review Gate: run the exact `DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P00_STATUS_PASS` inline Python command from `DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_MANIFEST.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P00_bootstrap.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P01_optional_dpf_plugin_lifecycle.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P01_optional_dpf_plugin_lifecycle_PROMPT.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P02_dpf_operator_metadata_normalization.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P02_dpf_operator_metadata_normalization_PROMPT.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P03_generic_dpf_runtime_adapter.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P03_generic_dpf_runtime_adapter_PROMPT.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P04_missing_plugin_placeholder_portability.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P04_missing_plugin_placeholder_portability_PROMPT.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P05_verification_docs_closeout.md`
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P05_verification_docs_closeout_PROMPT.md`
- This packet is documentation-only bootstrap work. Keep runtime, node, persistence, and test code untouched.
