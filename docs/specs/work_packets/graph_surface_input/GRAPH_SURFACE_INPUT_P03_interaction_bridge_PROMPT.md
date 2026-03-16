Implement GRAPH_SURFACE_INPUT_P03_interaction_bridge.md exactly. Before editing, read GRAPH_SURFACE_INPUT_MANIFEST.md, GRAPH_SURFACE_INPUT_STATUS.md, and GRAPH_SURFACE_INPUT_P03_interaction_bridge.md. Implement only P03. Preserve public QML/object contracts unless the packet explicitly introduces or removes one. Update GRAPH_SURFACE_INPUT_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks. Stop after P03; do not start P04.

Notes:
- Target branch: `codex/graph-surface-input/p03-interaction-bridge`.
- Preserve the existing inspector APIs; add the graph-surface-specific bridge path alongside them.
- Do not add new shared control components in this packet.
