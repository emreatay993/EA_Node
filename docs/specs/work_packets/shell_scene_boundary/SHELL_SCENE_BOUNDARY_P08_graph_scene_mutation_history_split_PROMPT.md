Implement SHELL_SCENE_BOUNDARY_P08_graph_scene_mutation_history_split.md exactly. Before editing, read SHELL_SCENE_BOUNDARY_MANIFEST.md, SHELL_SCENE_BOUNDARY_STATUS.md, and SHELL_SCENE_BOUNDARY_P08_graph_scene_mutation_history_split.md. Implement only P08. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, update SHELL_SCENE_BOUNDARY_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks, and stop after P08; do not start P09.

Notes:
- Target branch: `codex/shell-scene-boundary/p08-graph-scene-mutation-history-split`.
- Preserve explicit `nodeId` graph-surface property routing and current undo/history semantics.
- Do not extract payload-building or theme/media normalization work in this packet.
