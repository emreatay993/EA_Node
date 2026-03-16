Implement GRAPH_SURFACE_INPUT_P08_pointer_regression_audit.md exactly. Before editing, read GRAPH_SURFACE_INPUT_MANIFEST.md, GRAPH_SURFACE_INPUT_STATUS.md, and GRAPH_SURFACE_INPUT_P08_pointer_regression_audit.md. Implement only P08. Preserve public QML/object contracts unless the packet explicitly introduces or removes one. Update GRAPH_SURFACE_INPUT_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks. Stop after P08; do not start P09.

Notes:
- Target branch: `codex/graph-surface-input/p08-pointer-regression-audit`.
- This packet explicitly allows grep-backed audit coverage and reusable pointer-regression helpers.
- If the exact aggregate shell wrapper still exits with environment-specific code `5`, record the approved fresh-process fallback in the status ledger and use that fallback for the packet gate.
