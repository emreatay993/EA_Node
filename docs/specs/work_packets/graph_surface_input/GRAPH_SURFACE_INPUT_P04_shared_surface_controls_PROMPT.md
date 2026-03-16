Implement GRAPH_SURFACE_INPUT_P04_shared_surface_controls.md exactly. Before editing, read GRAPH_SURFACE_INPUT_MANIFEST.md, GRAPH_SURFACE_INPUT_STATUS.md, and GRAPH_SURFACE_INPUT_P04_shared_surface_controls.md. Implement only P04. Preserve public QML/object contracts unless the packet explicitly introduces or removes one. Update GRAPH_SURFACE_INPUT_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks. Stop after P04; do not start P05.

Notes:
- Target branch: `codex/graph-surface-input/p04-shared-surface-controls`.
- Reuse graph-surface semantics only. Do not import inspector widgets into graph-node surfaces.
- Keep the helper surface-control layer small and composable.
