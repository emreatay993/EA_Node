# Graph UX Work Packet Manifest

- Date: `2026-03-08`
- Scope baseline: graph-area UX improvements for the QML canvas and shell controls
- Canonical requirements: [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [UI/UX](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Architecture](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
- Runtime baseline: QML shell/canvas cutover is already present in `ea_node_editor/ui_qml/*` and `ea_node_editor/ui/shell/window.py`

## Packet Order (Strict)

1. `GRAPH_UX_P00_bootstrap.md`
2. `GRAPH_UX_P01_viewport_commands.md`
3. `GRAPH_UX_P02_undo_redo.md`
4. `GRAPH_UX_P03_drag_connect.md`
5. `GRAPH_UX_P04_graph_search.md`
6. `GRAPH_UX_P05_minimap.md`
7. `GRAPH_UX_P06_multi_move_duplicate.md`
8. `GRAPH_UX_P07_clipboard.md`
9. `GRAPH_UX_P08_layout_snap.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/graph-ux/p00-bootstrap` | Save the packet set into the repo and register it in the spec index |
| P01 Viewport Commands | `codex/graph-ux/p01-viewport-commands` | Shared camera/frame helpers and shortcuts |
| P02 Undo/Redo | `codex/graph-ux/p02-undo-redo` | Runtime-only history per workspace |
| P03 Drag Connect | `codex/graph-ux/p03-drag-connect` | Drag-to-connect port workflow |
| P04 Graph Search | `codex/graph-ux/p04-graph-search` | Cross-workspace graph search and jump |
| P05 Minimap | `codex/graph-ux/p05-minimap` | Minimap overlay and viewport navigation |
| P06 Multi-Move Duplicate | `codex/graph-ux/p06-multi-move-duplicate` | Multi-selection movement and duplicate |
| P07 Clipboard | `codex/graph-ux/p07-clipboard` | Copy/cut/paste graph fragments |
| P08 Layout Snap | `codex/graph-ux/p08-layout-snap` | Align/distribute tools and snap-to-grid |

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `GRAPH_UX_Pxx_<name>.md`
- Implementation prompt: `GRAPH_UX_Pxx_<name>_PROMPT.md`
- Status ledger update in [GRAPH_UX_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md):
  - branch label
  - commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Packet Template Rules

- Every packet spec must include: objective, preconditions, target subsystems, required behavior, non-goals, verification commands, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Do not start packet `N+1` before packet `N` is marked `PASS` in the status ledger.
- `P00` is documentation-only. `P01` through `P08` may change source/test files, but each thread must implement exactly one packet.
- Runtime-only state added by this roadmap stays non-persistent unless the packet explicitly says otherwise.
- Reuse helpers from earlier packets instead of reimplementing camera, history, or selection logic in later packets.
