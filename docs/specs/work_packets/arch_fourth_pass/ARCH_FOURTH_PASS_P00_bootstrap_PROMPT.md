Implement ARCH_FOURTH_PASS_P00_bootstrap.md exactly. Before editing, read ARCH_FOURTH_PASS_MANIFEST.md, ARCH_FOURTH_PASS_STATUS.md, and ARCH_FOURTH_PASS_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, run the full Verification Commands, create the packet docs, update ARCH_FOURTH_PASS_STATUS.md so `P00` is `PASS` and later packets remain `PENDING`, and stop after P00; do not start P01.

Notes:
- Target branch: `codex/arch-fourth-pass/p00-bootstrap`
- Review Gate: `none`
- This packet is documentation-only. Do not change runtime, source, or test files outside the bootstrap/index scope.
