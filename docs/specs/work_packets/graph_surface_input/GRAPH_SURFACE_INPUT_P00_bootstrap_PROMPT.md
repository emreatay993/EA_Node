Implement GRAPH_SURFACE_INPUT_P00_bootstrap.md exactly. Before editing, read GRAPH_SURFACE_INPUT_MANIFEST.md, GRAPH_SURFACE_INPUT_STATUS.md, and GRAPH_SURFACE_INPUT_P00_bootstrap.md. Implement only P00. Preserve public QML/object contracts unless the packet explicitly introduces or removes one. Update GRAPH_SURFACE_INPUT_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks. Stop after P00; do not start P01.

Constraints:
- Implement only the documentation bootstrap on branch `codex/graph-surface-input/p00-bootstrap`.
- Keep changes inside `docs/specs/work_packets/graph_surface_input/*`, `docs/specs/INDEX.md`, and `.gitignore` only if a narrow exception is required to track the new packet docs.
- Do not modify `ea_node_editor/**`, `tests/**`, `TODO.md`, `ARCHITECTURE.md`, or `docs/specs/requirements/**`.

Deliverables:
1. `GRAPH_SURFACE_INPUT` manifest and status ledger.
2. Packet contract and prompt files for `P00` through `P09`.
3. `docs/specs/INDEX.md` entries for the manifest and status ledger.
4. Verification command output summary.
