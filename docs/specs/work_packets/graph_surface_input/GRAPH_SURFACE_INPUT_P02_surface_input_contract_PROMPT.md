Implement GRAPH_SURFACE_INPUT_P02_surface_input_contract.md exactly. Before editing, read GRAPH_SURFACE_INPUT_MANIFEST.md, GRAPH_SURFACE_INPUT_STATUS.md, and GRAPH_SURFACE_INPUT_P02_surface_input_contract.md. Implement only P02. Preserve public QML/object contracts unless the packet explicitly introduces or removes one. Update GRAPH_SURFACE_INPUT_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks. Stop after P02; do not start P03.

Notes:
- Target branch: `codex/graph-surface-input/p02-surface-input-contract`.
- Keep `hoverActionHitRect` and `graphNodeSurfaceHoverActionButton` as compatibility-only shims in this packet.
- Do not add the shared surface-control kit yet.
