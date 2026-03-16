Implement GRAPH_SURFACE_INPUT_P06_inline_extended_editors.md exactly. Before editing, read GRAPH_SURFACE_INPUT_MANIFEST.md, GRAPH_SURFACE_INPUT_STATUS.md, and GRAPH_SURFACE_INPUT_P06_inline_extended_editors.md. Implement only P06. Preserve public QML/object contracts unless the packet explicitly introduces or removes one. Update GRAPH_SURFACE_INPUT_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks. Stop after P06; do not start P07.

Notes:
- Target branch: `codex/graph-surface-input/p06-inline-extended-editors`.
- Derive `textarea` and `path` commit/browse behavior from the inspector, but keep the implementation graph-surface-specific.
- Preserve current inspector APIs and layouts.
