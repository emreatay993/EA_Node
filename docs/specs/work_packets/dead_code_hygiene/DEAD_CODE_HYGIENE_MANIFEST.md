# DEAD_CODE_HYGIENE Work Packet Manifest

- Date: `2026-03-18`
- Scope baseline: balanced dead-code cleanup across runtime code and directly related tests, with no intentional feature loss, no UI change, and no serializer/schema changes.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Execution Engine](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/50_EXECUTION_ENGINE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `SHELL_SCENE_BOUNDARY` already migrated library/search, workspace/run/title/console, and inspector-owned concerns onto `shellLibraryBridge`, `shellWorkspaceBridge`, and `shellInspectorBridge`, but `ea_node_editor/ui_qml/MainShell.qml` still passes compatibility plumbing that several owned shell components no longer read locally.
  - The exact unread QML properties requested for cleanup are still declared on `NodeLibraryPane.qml`, `GraphSearchOverlay.qml`, `ConnectionQuickInsertOverlay.qml`, `GraphHintOverlay.qml`, `LibraryWorkflowContextPopup.qml`, `ScriptEditorOverlay.qml`, `ShellRunToolbar.qml`, `ShellTitleBar.qml`, `InspectorPane.qml`, and `WorkspaceCenterPane.qml`, with the assignments still present in `MainShell.qml`.
  - `WorkspaceCenterPane.qml` now reads tabs, console, and workspace/run state through `shellWorkspaceBridge`, so `workspaceTabsBridgeRef` and `consoleBridgeRef` appear to be declaration leftovers; `sceneBridgeRef` and `viewBridgeRef` still feed `GraphCanvas`.
  - `overlayHostItem` is still read by `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`, and `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`, so it is not currently a confirmed dead surface.
  - `ea_node_editor/execution/protocol.py`, `ea_node_editor/ui/shell/library_flow.py`, and `ea_node_editor/ui_qml/edge_routing.py` contain the targeted helper functions `dict_to_event_type`, `input_port_is_available`, and `inline_body_height`; a project-venv `vulture` run flags those helpers as unused but also reports broader out-of-scope candidates that this packet set must not sweep in.

## Packet Order (Strict)

1. `DEAD_CODE_HYGIENE_P00_bootstrap.md`
2. `DEAD_CODE_HYGIENE_P01_qml_shell_plumbing_cleanup.md`
3. `DEAD_CODE_HYGIENE_P02_internal_python_helper_cleanup.md`
4. `DEAD_CODE_HYGIENE_P03_regression_locks.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/dead-code-hygiene/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 QML Shell Plumbing Cleanup | `codex/dead-code-hygiene/p01-qml-shell-plumbing-cleanup` | Remove provably unread shell-surface property declarations and call-site assignments without changing bridge/context contracts |
| P02 Internal Python Helper Cleanup | `codex/dead-code-hygiene/p02-internal-python-helper-cleanup` | Remove the approved internal dead helpers and only the directly adjacent dead imports in the touched modules |
| P03 Regression Locks | `codex/dead-code-hygiene/p03-regression-locks` | Tighten static regression coverage so the removed QML plumbing and Python helpers do not silently return |

## Locked Defaults

- Preserve current user-facing behavior, visuals, menus, workflow semantics, persistence schema, and bridge object names.
- Preserve public-looking Python surfaces unless they are clearly private and explicitly inside this packet scope.
- Do not remove global QML context properties or rename their registered names: `mainWindow`, `sceneBridge`, `viewBridge`, `consoleBridge`, `workspaceTabsBridge`, `shellLibraryBridge`, `shellWorkspaceBridge`, `shellInspectorBridge`, and `graphCanvasBridge`.
- Do not remove inspector selected-node APIs in this packet set; the cleanup may remove only unread local property plumbing, not the underlying selected-node compatibility surface.
- Keep `sceneBridgeRef`, `viewBridgeRef`, `graphCanvas` object identity, and the existing `GraphCanvas` integration methods stable.
- `overlayHostItem` may be removed only if the packet executor proves there are no remaining runtime reads after caller plumbing is deleted; otherwise it must stay and the retention must be recorded in the packet wrap-up and status ledger.
- Internal Python symbol removals in this packet set are limited to `dict_to_event_type`, `input_port_is_available`, and `inline_body_height`, plus only the directly adjacent import cleanup made dead by those removals.
- Explicit out-of-scope retained surfaces include `AsyncNodePlugin`, `icon_names`, `list_installed_packages`, `uninstall_package`, and package `__init__` re-export surfaces even if local tooling reports them as unused.
- Execution is strictly sequential with one packet per wave.
- The worktree is already dirty from `graph_canvas_perf` packet docs plus `docs/specs/INDEX.md` and `.gitignore` edits, and it also contains unrelated untracked `ea_node_editor.egg-info/`; no `DEAD_CODE_HYGIENE` packet may revert, restage, or otherwise disturb unrelated changes.
- Use the project venv for verification commands: `./venv/Scripts/python.exe`.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `DEAD_CODE_HYGIENE_Pxx_<name>.md`
- Implementation prompt: `DEAD_CODE_HYGIENE_Pxx_<name>_PROMPT.md`
- Status ledger update in [DEAD_CODE_HYGIENE_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement DEAD_CODE_HYGIENE_PXX_<name>.md exactly. Before editing, read DEAD_CODE_HYGIENE_MANIFEST.md, DEAD_CODE_HYGIENE_STATUS.md, and DEAD_CODE_HYGIENE_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve public QML/object contracts and public-looking Python surfaces unless the packet explicitly removes an approved dead seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update DEAD_CODE_HYGIENE_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P03` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Keep the current shell bridge/context-property registrations intact throughout this packet set.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
