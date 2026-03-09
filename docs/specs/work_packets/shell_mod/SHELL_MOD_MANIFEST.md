# SHELL_MOD Work Packet Manifest

- Date: `2026-03-09`
- Scope baseline: modular refactor of the shell window and workspace controller without intentional runtime feature changes.
- Canonical requirements: [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Persistence](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
- Runtime baseline: `ea_node_editor/ui/shell/window.py` and `ea_node_editor/ui/shell/controllers/workspace_library_controller.py` are the primary large modules targeted by this packet set.

## Packet Order (Strict)

1. `SHELL_MOD_P00_bootstrap.md`
2. `SHELL_MOD_P01_window_delegate_cleanup.md`
3. `SHELL_MOD_P02_window_actions_menus.md`
4. `SHELL_MOD_P03_window_library_inspector.md`
5. `SHELL_MOD_P04_window_search_scope_state.md`
6. `SHELL_MOD_P05_workspace_view_nav.md`
7. `SHELL_MOD_P06_workspace_drop_connect.md`
8. `SHELL_MOD_P07_workspace_edit_ops.md`
9. `SHELL_MOD_P08_workspace_io_tests.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/shell-mod/p00-bootstrap` | Save the packet set into the repo and register it in the spec index |
| P01 Window Delegate Cleanup | `codex/shell-mod/p01-window-delegate-cleanup` | Replace dynamic delegation with explicit call surfaces |
| P02 Window Actions Menus | `codex/shell-mod/p02-window-actions-menus` | Extract action and menu wiring helpers |
| P03 Window Library Inspector | `codex/shell-mod/p03-window-library-inspector` | Extract library and inspector payload shaping helpers |
| P04 Window Search Scope State | `codex/shell-mod/p04-window-search-scope-state` | Extract graph-search, scope-camera, hint, and snap state helpers |
| P05 Workspace View Nav | `codex/shell-mod/p05-workspace-view-nav` | Extract workspace/view navigation and graph jump/focus flows |
| P06 Workspace Drop Connect | `codex/shell-mod/p06-workspace-drop-connect` | Extract node drop, insert, and auto-connect orchestration |
| P07 Workspace Edit Ops | `codex/shell-mod/p07-workspace-edit-ops` | Extract edit operations, clipboard, history, and graph mutation wrappers |
| P08 Workspace IO Tests | `codex/shell-mod/p08-workspace-io-tests` | Extract controller IO flows and modularize oversized shell/controller tests |

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `SHELL_MOD_Pxx_<name>.md`
- Implementation prompt: `SHELL_MOD_Pxx_<name>_PROMPT.md`
- Status ledger update in [SHELL_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md):
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
- Keep QML-facing `@pyqtSlot` and `@pyqtProperty` signatures stable across packets.
- Prefer composition helpers over dynamic delegation for shell/controller modularization.
