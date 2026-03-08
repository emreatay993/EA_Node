# GRAPH_UX P00: Bootstrap Packet Set

## Objective
- Save the Graph UX roadmap into the repo as a packet set and register it in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No Graph UX packet set exists yet under `docs/specs/work_packets/graph_ux/`.

## Target Subsystems
- `docs/specs/work_packets/graph_ux/*`
- `docs/specs/INDEX.md`

## Required Behavior
- Create `docs/specs/work_packets/graph_ux/`.
- Add `GRAPH_UX_MANIFEST.md` and `GRAPH_UX_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P08` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the Graph UX manifest and status ledger.
- Mark `P00` as `PASS` in `GRAPH_UX_STATUS.md` and leave `P01` through `P08` as `PENDING`.
- Make no product/runtime/test changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No requirement rewrites under `docs/specs/requirements/**`.

## Verification Commands
1. `& { $required = @('docs/specs/work_packets/graph_ux/GRAPH_UX_MANIFEST.md','docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P00_bootstrap.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P00_bootstrap_PROMPT.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P01_viewport_commands.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P01_viewport_commands_PROMPT.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P02_undo_redo.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P02_undo_redo_PROMPT.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P03_drag_connect.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P03_drag_connect_PROMPT.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P04_graph_search.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P04_graph_search_PROMPT.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P05_minimap.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P05_minimap_PROMPT.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P06_multi_move_duplicate.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P06_multi_move_duplicate_PROMPT.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P07_clipboard.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P07_clipboard_PROMPT.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P08_layout_snap.md','docs/specs/work_packets/graph_ux/GRAPH_UX_P08_layout_snap_PROMPT.md'); $missing = $required | Where-Object { -not (Test-Path $_) }; if ($missing) { Write-Output ('MISSING: ' + ($missing -join ', ')); exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'Graph UX Work Packet Manifest' -Quiet)) { Write-Output 'INDEX_MISSING_GRAPH_UX_MANIFEST'; exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'Graph UX Status Ledger' -Quiet)) { Write-Output 'INDEX_MISSING_GRAPH_UX_STATUS'; exit 1 }; Write-Output 'GRAPH_UX_P00_FILE_GATE_PASS' }`

## Acceptance Criteria
- The verification command returns `GRAPH_UX_P00_FILE_GATE_PASS`.
- `GRAPH_UX_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are the new `graph_ux` packet docs and `docs/specs/INDEX.md`.

## Handoff Notes
- The next thread must read `GRAPH_UX_MANIFEST.md`, `GRAPH_UX_STATUS.md`, and `GRAPH_UX_P01_viewport_commands.md` before editing code.
- `P01` is the first code packet; it must not rewrite or reorganize the packet set.
