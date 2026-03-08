# SUBNODE P00: Bootstrap Packet Set

## Objective
- Save the Subnode roadmap into the repo as a packet set and register it in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No Subnode packet set exists yet under `docs/specs/work_packets/subnode/`.

## Target Subsystems
- `docs/specs/work_packets/subnode/*`
- `docs/specs/INDEX.md`

## Required Behavior
- Create `docs/specs/work_packets/subnode/`.
- Add `SUBNODE_MANIFEST.md` and `SUBNODE_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P09` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the Subnode manifest and status ledger.
- Mark `P00` as `PASS` in `SUBNODE_STATUS.md` and leave `P01` through `P09` as `PENDING`.
- Make no product/runtime/test changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No requirement rewrites under `docs/specs/requirements/**`.

## Verification Commands
1. `& { $required = @('docs/specs/work_packets/subnode/SUBNODE_MANIFEST.md','docs/specs/work_packets/subnode/SUBNODE_STATUS.md','docs/specs/work_packets/subnode/SUBNODE_P00_bootstrap.md','docs/specs/work_packets/subnode/SUBNODE_P00_bootstrap_PROMPT.md','docs/specs/work_packets/subnode/SUBNODE_P01_hierarchy_persistence.md','docs/specs/work_packets/subnode/SUBNODE_P01_hierarchy_persistence_PROMPT.md','docs/specs/work_packets/subnode/SUBNODE_P02_dynamic_port_resolution.md','docs/specs/work_packets/subnode/SUBNODE_P02_dynamic_port_resolution_PROMPT.md','docs/specs/work_packets/subnode/SUBNODE_P03_scope_navigation.md','docs/specs/work_packets/subnode/SUBNODE_P03_scope_navigation_PROMPT.md','docs/specs/work_packets/subnode/SUBNODE_P04_group_and_ungroup.md','docs/specs/work_packets/subnode/SUBNODE_P04_group_and_ungroup_PROMPT.md','docs/specs/work_packets/subnode/SUBNODE_P05_hierarchy_graph_ops.md','docs/specs/work_packets/subnode/SUBNODE_P05_hierarchy_graph_ops_PROMPT.md','docs/specs/work_packets/subnode/SUBNODE_P06_pin_editing_ux.md','docs/specs/work_packets/subnode/SUBNODE_P06_pin_editing_ux_PROMPT.md','docs/specs/work_packets/subnode/SUBNODE_P07_execution_compiler.md','docs/specs/work_packets/subnode/SUBNODE_P07_execution_compiler_PROMPT.md','docs/specs/work_packets/subnode/SUBNODE_P08_custom_workflow_library.md','docs/specs/work_packets/subnode/SUBNODE_P08_custom_workflow_library_PROMPT.md','docs/specs/work_packets/subnode/SUBNODE_P09_import_export_qa.md','docs/specs/work_packets/subnode/SUBNODE_P09_import_export_qa_PROMPT.md'); $missing = $required | Where-Object { -not (Test-Path $_) }; if ($missing) { Write-Output ('MISSING: ' + ($missing -join ', ')); exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'Subnode Work Packet Manifest' -Quiet)) { Write-Output 'INDEX_MISSING_SUBNODE_MANIFEST'; exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'Subnode Status Ledger' -Quiet)) { Write-Output 'INDEX_MISSING_SUBNODE_STATUS'; exit 1 }; Write-Output 'SUBNODE_P00_FILE_GATE_PASS' }`

## Acceptance Criteria
- The verification command returns `SUBNODE_P00_FILE_GATE_PASS`.
- `SUBNODE_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are the new `subnode` packet docs and `docs/specs/INDEX.md`.

## Handoff Notes
- The next thread must read `SUBNODE_MANIFEST.md`, `SUBNODE_STATUS.md`, and `SUBNODE_P01_hierarchy_persistence.md` before editing code.
- `P01` is the first code packet; it must not rewrite or reorganize the packet set.
