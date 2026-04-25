Implement COMMENT_FLOATING_POPOVER_P00_bootstrap.md exactly. Before editing, read COMMENT_FLOATING_POPOVER_MANIFEST.md, COMMENT_FLOATING_POPOVER_STATUS.md, and COMMENT_FLOATING_POPOVER_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, and stop after P00; do not start P01.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Bootstrap notes:
- Target branch: `codex/comment-floating-popover/p00-bootstrap`.
- Review Gate: the inline `COMMENT_FLOATING_POPOVER_P00_STATUS_PASS` check in the packet spec.
- Expected artifacts are the manifest, status ledger, `P00` through `P03` specs, matching `*_PROMPT.md` files, and `docs/specs/INDEX.md`.
- Implementation worker packets in this packet set must use `gpt-5.5` with `xhigh` reasoning when later executed by the subagent executor.
- This packet is documentation-only. Do not edit runtime code, tests, scripts, requirements docs, or performance docs.
