# SHELL_MOD P00: Bootstrap Packet Set

## Objective
- Save the SHELL_MOD roadmap into the repo and register it in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No SHELL_MOD packet set exists yet under `docs/specs/work_packets/shell_mod/`.

## Target Subsystems
- `docs/specs/work_packets/shell_mod/*`
- `docs/specs/INDEX.md`

## Required Behavior
- Create `docs/specs/work_packets/shell_mod/`.
- Add `SHELL_MOD_MANIFEST.md` and `SHELL_MOD_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P08` using canonical naming.
- Update `docs/specs/INDEX.md` with links to the SHELL_MOD manifest and status ledger.
- Mark `P00` as `PASS` in `SHELL_MOD_STATUS.md` and leave `P01` through `P08` as `PENDING`.
- Make no product/runtime/test changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No requirement rewrites under `docs/specs/requirements/**`.

## Verification Commands
1. `& { $required = @('docs/specs/work_packets/shell_mod/SHELL_MOD_MANIFEST.md','docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P00_bootstrap.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P00_bootstrap_PROMPT.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P01_window_delegate_cleanup.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P01_window_delegate_cleanup_PROMPT.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P02_window_actions_menus.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P02_window_actions_menus_PROMPT.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P03_window_library_inspector.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P03_window_library_inspector_PROMPT.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P04_window_search_scope_state.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P04_window_search_scope_state_PROMPT.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P05_workspace_view_nav.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P05_workspace_view_nav_PROMPT.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P06_workspace_drop_connect.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P06_workspace_drop_connect_PROMPT.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P07_workspace_edit_ops.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P07_workspace_edit_ops_PROMPT.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P08_workspace_io_tests.md','docs/specs/work_packets/shell_mod/SHELL_MOD_P08_workspace_io_tests_PROMPT.md'); $missing = $required | Where-Object { -not (Test-Path $_) }; if ($missing) { Write-Output ('MISSING: ' + ($missing -join ', ')); exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'SHELL_MOD Work Packet Manifest' -Quiet)) { Write-Output 'INDEX_MISSING_SHELL_MOD_MANIFEST'; exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'SHELL_MOD Status Ledger' -Quiet)) { Write-Output 'INDEX_MISSING_SHELL_MOD_STATUS'; exit 1 }; Write-Output 'SHELL_MOD_P00_FILE_GATE_PASS' }`

## Acceptance Criteria
- The verification command returns `SHELL_MOD_P00_FILE_GATE_PASS`.
- `SHELL_MOD_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- Only bootstrap docs and index registration are changed.

## Handoff Notes
- The next thread must read `SHELL_MOD_MANIFEST.md`, `SHELL_MOD_STATUS.md`, and `SHELL_MOD_P01_window_delegate_cleanup.md` before editing code.
- `P01` is the first code packet and must not modify packet definitions.
