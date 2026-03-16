Implement GRAPH_SURFACE_INPUT_P07_media_surface_migration.md exactly. Before editing, read GRAPH_SURFACE_INPUT_MANIFEST.md, GRAPH_SURFACE_INPUT_STATUS.md, and GRAPH_SURFACE_INPUT_P07_media_surface_migration.md. Implement only P07. Preserve public QML/object contracts unless the packet explicitly introduces or removes one. Update GRAPH_SURFACE_INPUT_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks. Stop after P07; do not start P08.

Notes:
- Target branch: `codex/graph-surface-input/p07-media-surface-migration`.
- This packet explicitly allows removing `hoverActionHitRect` and `graphNodeSurfaceHoverActionButton`.
- Preserve crop-mode `blocksHostInteraction` behavior while removing the hover proxy.
