# COMMENT_BACKDROP Work Packet Manifest

- Date: `2026-03-22`
- Scope baseline: add a PyFlow-style comment backdrop/group primitive as a dedicated passive canvas item that stays distinct from the existing annotation cards, using geometry-owned membership, nested backdrops, drag-with-contents, collapse/hide, boundary-edge rerouting, wrap-selection creation, and inline plus inspector editing without disturbing the current subnode grouping flow.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node SDK](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/nodes/builtins/passive_annotation.py` and `ea_node_editor/ui_qml/components/graph/passive/GraphAnnotationNoteSurface.qml` currently implement note-style annotation cards with passive ports, not background grouping items.
  - `ea_node_editor/ui_qml/graph_scene_payload_builder.py` and `ea_node_editor/ui_qml/graph_scene_bridge.py` only publish node, minimap-node, and edge payloads, and `ea_node_editor/ui_qml/components/GraphCanvas.qml` renders one node repeater above `graphCanvasEdgeLayer`.
  - `ea_node_editor/ui/shell/window_actions.py` reserves `Ctrl+G` and `Ctrl+Shift+G` for structural subnode grouping and ungrouping, and there is no wrap-selection-in-comment action or `C` shortcut.
  - `ea_node_editor/ui/shell/runtime_clipboard.py`, `ea_node_editor/graph/transforms.py`, and the current delete flows do not define backdrop-specific copy, delete, paste, or load semantics.

## Packet Order (Strict)

1. `COMMENT_BACKDROP_P00_bootstrap.md`
2. `COMMENT_BACKDROP_P01_catalog_surface_contract.md`
3. `COMMENT_BACKDROP_P02_backdrop_layer_bridge_split.md`
4. `COMMENT_BACKDROP_P03_geometry_membership_wrap_selection.md`
5. `COMMENT_BACKDROP_P04_drag_resize_nested_motion.md`
6. `COMMENT_BACKDROP_P05_collapse_boundary_edge_routing.md`
7. `COMMENT_BACKDROP_P06_editing_shell_creation_affordances.md`
8. `COMMENT_BACKDROP_P07_clipboard_delete_load_recompute.md`
9. `COMMENT_BACKDROP_P08_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/comment-backdrop/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Catalog + Surface Contract | `codex/comment-backdrop/p01-catalog-surface-contract` | Add the dedicated backdrop node type, surface family, metric contract, and basic host-path rendering foundation |
| P02 Backdrop Layer + Bridge Split | `codex/comment-backdrop/p02-backdrop-layer-bridge-split` | Split backdrop payloads into a dedicated scene and canvas layer below edges and regular nodes |
| P03 Geometry Membership + Wrap Selection | `codex/comment-backdrop/p03-geometry-membership-wrap-selection` | Add derived ownership, nesting, and the backend wrap-selection transaction without shell shortcuts yet |
| P04 Drag/Resize + Nested Motion | `codex/comment-backdrop/p04-drag-resize-nested-motion` | Make backdrop drag and resize move descendants correctly and record coherent history |
| P05 Collapse + Boundary Edge Routing | `codex/comment-backdrop/p05-collapse-boundary-edge-routing` | Hide descendants on collapse and reroute boundary edges to the collapsed backdrop perimeter |
| P06 Editing + Shell Creation Affordances | `codex/comment-backdrop/p06-editing-shell-creation-affordances` | Wire library placement, `C` wrap-selection, and inline plus inspector editing without disturbing subnode grouping |
| P07 Clipboard + Delete + Load Recompute | `codex/comment-backdrop/p07-clipboard-delete-load-recompute` | Lock expanded versus collapsed clipboard and delete behavior and recompute ownership on paste and load |
| P08 Docs + Traceability Closeout | `codex/comment-backdrop/p08-docs-traceability-closeout` | Refresh docs, requirements, and traceability after the feature packets land |

## Locked Defaults

- The new backdrop node is `passive.annotation.comment_backdrop`, `runtime_behavior="passive"`, `surface_family="comment_backdrop"`, `surface_variant="comment_backdrop"`, zero-port, and `collapsible=True`.
- Existing `passive.annotation.sticky_note`, `passive.annotation.callout`, and `passive.annotation.section_header` remain connectable note-style annotations and must not gain backdrop or grouping semantics in this packet set.
- Membership is derived, not persisted. Direct ownership always resolves to the smallest backdrop in the same scope and parent chain whose bounds fully contain the candidate node or nested backdrop. Partial overlap never counts.
- Comment backdrops render on a dedicated layer below `graphCanvasEdgeLayer` and the regular node layer. Existing annotation cards remain on the normal node layer.
- Backdrops must never absorb nodes across subnode scope boundaries or parent-chain boundaries.
- Wrap-selection creation uses shortcut `C`. `Ctrl+G` and `Ctrl+Shift+G` remain the structural subnode group and ungroup shortcuts.
- Expanded backdrop copy and delete affect only explicitly selected items. Collapsed backdrop copy and delete implicitly include descendant backdrops, descendant nodes, and fully internal edges.
- Title editing reuses the shared header inline-title path. Body editing is supported both inline on the canvas and through the inspector.
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

### Wave 5
- `P05`

### Wave 6
- `P06`

### Wave 7
- `P07`

### Wave 8
- `P08`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `COMMENT_BACKDROP_Pxx_<name>.md`
- Implementation prompt: `COMMENT_BACKDROP_Pxx_<name>_PROMPT.md`
- Packet wrap-up artifact for each implementation packet: `docs/specs/work_packets/comment_backdrop/Pxx_<slug>_WRAPUP.md`
- Status ledger update in [COMMENT_BACKDROP_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement COMMENT_BACKDROP_PXX_<name>.md exactly. Before editing, read COMMENT_BACKDROP_MANIFEST.md, COMMENT_BACKDROP_STATUS.md, and COMMENT_BACKDROP_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and public comment-backdrop, canvas, graph-surface-input, and shell contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update COMMENT_BACKDROP_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P08` may change source, test, and docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Keep public `graphCanvas`, `graphNodeCard`, `graphCanvasEdgeLayer`, `GraphCanvasBridge`, `GraphSceneBridge`, `ShellWindow`, and existing subnode grouping contracts stable unless the owning packet explicitly changes a packet-owned seam.
- Reuse the current `PASSIVE_NODES`, `GRAPH_SURFACE_INPUT`, `NODE_INLINE_TITLES`, and shell-controller seams instead of reopening monolithic code paths without packet-owned cause.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
