Implement SHELL_SCENE_BOUNDARY_P02_qml_context_bootstrap.md exactly. Before editing, read SHELL_SCENE_BOUNDARY_MANIFEST.md, SHELL_SCENE_BOUNDARY_STATUS.md, and SHELL_SCENE_BOUNDARY_P02_qml_context_bootstrap.md. Implement only P02. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, update SHELL_SCENE_BOUNDARY_STATUS.md with branch label, commit sha, commands, tests, artifacts, and residual risks, and stop after P02; do not start P03.

Notes:
- Target branch: `codex/shell-scene-boundary/p02-qml-context-bootstrap`.
- Create the bootstrap module and bridge skeletons, but do not migrate QML consumers yet.
- Keep the legacy context properties available for later waves.
