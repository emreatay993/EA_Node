Implement NESTED_NODE_CATEGORIES_P00_bootstrap.md exactly. Before editing, read NESTED_NODE_CATEGORIES_MANIFEST.md, NESTED_NODE_CATEGORIES_STATUS.md, and NESTED_NODE_CATEGORIES_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update NESTED_NODE_CATEGORIES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Notes:
- Target branch: `codex/nested-node-categories/p00-bootstrap`.
- Review Gate: the inline `NESTED_NODE_CATEGORIES_P00_STATUS_PASS` check in `NESTED_NODE_CATEGORIES_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/nested_node_categories/*`
- Keep `P00` limited to bootstrap docs and index/ignore registration only. Do not begin runtime implementation work.
