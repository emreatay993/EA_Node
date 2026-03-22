# NODE_INLINE_TITLES Work Packet Manifest

- Date: `2026-03-22`
- Scope baseline: extend the existing flowchart-only inline node-title editing into a shared all-node capability without forking the workflow, while preserving subnode scope entry and the current rename/history architecture.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node SDK](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml` already contains the shared title editor, but it is gated by `flowchartTitleEditable` and therefore only activates for flowchart surfaces.
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml` currently routes inline header commits through `set_node_property(nodeId, key, value)`, which is safe for passive families with a declared `title` property but does not generalize to standard nodes that only own `node.title`.
  - `ea_node_editor/ui_qml/graph_scene_mutation_history.py` already centralizes `set_node_title(...)` and surface-title syncing for flowchart/planning/annotation families, but `set_node_property(..., "title", ...)` and `set_node_properties(..., {"title": ...})` still live on a separate path.
  - Scope-capable subnode shells still rely on the existing `nodeOpenRequested` -> `GraphCanvas.requestOpenSubnodeScope(...)` route, and the header `OPEN` badge is currently visual-only rather than an interactive replacement affordance.

## Packet Order (Strict)

1. `NODE_INLINE_TITLES_P00_bootstrap.md`
2. `NODE_INLINE_TITLES_P01_title_mutation_authority.md`
3. `NODE_INLINE_TITLES_P02_shared_header_title_rollout.md`
4. `NODE_INLINE_TITLES_P03_scoped_title_edit_integration.md`
5. `NODE_INLINE_TITLES_P04_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/node-inline-titles/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Title Mutation Authority | `codex/node-inline-titles/p01-title-mutation-authority` | Converge all title mutations on the existing rename authority so inline title edits do not fork the graph-mutation path |
| P02 Shared Header Title Rollout | `codex/node-inline-titles/p02-shared-header-title-rollout` | Generalize the shared header editor to non-scoped node families without adding per-surface title workflows |
| P03 Scoped Title Edit Integration | `codex/node-inline-titles/p03-scoped-title-edit-integration` | Preserve subnode scope entry through an interactive `OPEN` badge, enable scoped/collapsed inline title edits, and freeze the end-to-end regressions |
| P04 Docs And Traceability Closeout | `codex/node-inline-titles/p04-docs-traceability-closeout` | Refresh architecture/README/requirements traceability for the new shared inline-title workflow |

## Locked Defaults

- There is exactly one inline node-title editor for this scope: the shared header-layer `graphNodeTitleEditor`. Do not add per-surface title editors or a second rename workflow.
- Empty or whitespace-only inline title commits remain rejected; trimming behavior stays aligned with the existing rename path.
- Title edits must converge on `set_node_title(...)` semantics at the mutation layer. Property-backed passive families keep `node.title` and `properties["title"]` synchronized, while standard/media/subnode nodes update only the canonical node title unless a packet explicitly says otherwise.
- Context-menu rename, `F2`, and any other existing rename entry points remain supported and must keep using the same underlying title authority rather than a packet-owned fork.
- Subnode scope entry is preserved through an interactive `OPEN` badge. Title double-click becomes the edit gesture even on scope-capable nodes once `P03` lands.
- Collapsed nodes are in scope for the final behavior, but only `P03` may unlock collapsed/scoped title editing.
- This packet set is intentionally sequential. No implementation wave contains more than one packet.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

### Wave 4
- `P04`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `NODE_INLINE_TITLES_Pxx_<name>.md`
- Implementation prompt: `NODE_INLINE_TITLES_Pxx_<name>_PROMPT.md`
- Status ledger update in [NODE_INLINE_TITLES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement NODE_INLINE_TITLES_PXX_<name>.md exactly. Before editing, read NODE_INLINE_TITLES_MANIFEST.md, NODE_INLINE_TITLES_STATUS.md, and NODE_INLINE_TITLES_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and public graph-title/scope-entry contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update NODE_INLINE_TITLES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P04` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Keep public `graphNodeCard`, `graphCanvas`, `GraphCanvasBridge`, `GraphCanvasCommandBridge`, `GraphSceneBridge`, and `ShellWindow.request_rename_node(...)` contracts stable unless the owning packet explicitly changes a packet-owned seam.
- Reuse the current `GRAPH_SURFACE_INPUT`, `QML_SURFACE_MOD`, and `ARCH_SIXTH_PASS` seams instead of reopening monolithic files without packet-owned cause.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
