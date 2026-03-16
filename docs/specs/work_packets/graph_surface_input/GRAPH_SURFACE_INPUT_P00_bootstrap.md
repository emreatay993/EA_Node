# GRAPH_SURFACE_INPUT P00: Bootstrap

## Objective
- Establish the `GRAPH_SURFACE_INPUT` packet set, initialize the status ledger, and register the packet docs in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `graph_surface_input` packet set exists yet under `docs/specs/work_packets/`.

## Target Subsystems
- `.gitignore` only for a narrow exception if needed to make the new packet docs trackable
- `docs/specs/work_packets/graph_surface_input/*`
- `docs/specs/INDEX.md`

## Required Behavior
- Create `docs/specs/work_packets/graph_surface_input/`.
- Add `GRAPH_SURFACE_INPUT_MANIFEST.md` and `GRAPH_SURFACE_INPUT_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P09` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `GRAPH_SURFACE_INPUT` manifest and status ledger.
- Add a narrow `.gitignore` exception if needed so the new packet docs are not ignored by git.
- Mark `P00` as `PASS` in `GRAPH_SURFACE_INPUT_STATUS.md` and leave `P01` through `P09` as `PENDING`.
- Keep the packet order, branch labels, prompt shell, and locked defaults aligned with the approved roadmap.
- Make no runtime, source, or test changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to `TODO.md`, `ARCHITECTURE.md`, or requirements docs in this packet.

## Verification Commands
1. `& { $required = @('docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_MANIFEST.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P00_bootstrap.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P00_bootstrap_PROMPT.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P01_host_drag_layer_foundation.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P01_host_drag_layer_foundation_PROMPT.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P02_surface_input_contract.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P02_surface_input_contract_PROMPT.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P03_interaction_bridge.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P03_interaction_bridge_PROMPT.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P04_shared_surface_controls.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P04_shared_surface_controls_PROMPT.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P05_inline_core_editors.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P05_inline_core_editors_PROMPT.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P06_inline_extended_editors.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P06_inline_extended_editors_PROMPT.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P07_media_surface_migration.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P07_media_surface_migration_PROMPT.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P08_pointer_regression_audit.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P08_pointer_regression_audit_PROMPT.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P09_docs_traceability.md','docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_P09_docs_traceability_PROMPT.md'); $missing = $required | Where-Object { -not (Test-Path $_) }; if ($missing) { Write-Output ('MISSING: ' + ($missing -join ', ')); exit 1 }; git check-ignore docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_MANIFEST.md *> $null; if ($LASTEXITCODE -eq 0) { Write-Output 'GRAPH_SURFACE_INPUT_DOCS_IGNORED'; exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'GRAPH_SURFACE_INPUT Work Packet Manifest' -Quiet)) { Write-Output 'INDEX_MISSING_GRAPH_SURFACE_INPUT_MANIFEST'; exit 1 }; if (-not (Select-String -Path 'docs/specs/INDEX.md' -Pattern 'GRAPH_SURFACE_INPUT Status Ledger' -Quiet)) { Write-Output 'INDEX_MISSING_GRAPH_SURFACE_INPUT_STATUS'; exit 1 }; Write-Output 'GRAPH_SURFACE_INPUT_P00_FILE_GATE_PASS' }`

## Acceptance Criteria
- The verification command returns `GRAPH_SURFACE_INPUT_P00_FILE_GATE_PASS`.
- The verification command confirms the new packet docs are not ignored by git.
- `GRAPH_SURFACE_INPUT_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore` if needed for packet tracking, the new `graph_surface_input` packet docs, and `docs/specs/INDEX.md`.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `GRAPH_SURFACE_INPUT_MANIFEST.md`, `GRAPH_SURFACE_INPUT_STATUS.md`, and `GRAPH_SURFACE_INPUT_P01_host_drag_layer_foundation.md` before editing code.
