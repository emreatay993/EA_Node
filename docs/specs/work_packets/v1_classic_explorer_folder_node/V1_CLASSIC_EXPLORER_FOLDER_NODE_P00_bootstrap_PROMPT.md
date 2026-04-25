Implement V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_bootstrap.md exactly. Before editing, read V1_CLASSIC_EXPLORER_FOLDER_NODE_MANIFEST.md, V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md, and V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet artifacts, update V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- P00 creates the packet docs and status ledger; it does not require a separate `P00_*_WRAPUP.md` artifact.
- Keep `P00` as `PASS` and every later packet as `PENDING`.
- Treat `Commit Owner` values in later wrap-ups as packet-contract tokens (`worker`, `executor`, or `executor-pending`), not usernames or email addresses.
- Commit the bootstrap docs before starting executor-created implementation worktrees.

Notes:
- Target branch: `codex/v1-classic-explorer-folder-node/p00-bootstrap`
- Review Gate: the inline `V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_STATUS_PASS` command in the P00 spec
- Expected artifacts: manifest, status ledger, all P00-P07 spec files, all P00-P07 prompt files, and the `docs/specs/INDEX.md` registration.
