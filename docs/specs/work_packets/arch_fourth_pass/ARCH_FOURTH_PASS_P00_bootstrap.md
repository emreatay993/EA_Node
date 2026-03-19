# ARCH_FOURTH_PASS P00: Bootstrap

## Objective
- Establish the `ARCH_FOURTH_PASS` packet set, initialize the status ledger, register the docs in the canonical spec index, and add a narrow `.gitignore` exception only if verification shows the new packet docs would otherwise be ignored.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `arch_fourth_pass` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only if the new packet docs are ignored by git
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_fourth_pass/*`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_fourth_pass/**`

## Required Behavior
- Create `docs/specs/work_packets/arch_fourth_pass/`.
- Add `ARCH_FOURTH_PASS_MANIFEST.md` and `ARCH_FOURTH_PASS_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P08` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `ARCH_FOURTH_PASS` manifest and status ledger.
- Mark `P00` as `PASS` in `ARCH_FOURTH_PASS_STATUS.md` and leave `P01` through `P08` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, review gates, expected artifacts, and fresh-thread prompt shell in the packet docs.
- Add a narrow `.gitignore` exception only if the verification command proves the new packet docs are ignored.
- Make no runtime, source, or test changes outside the documentation/bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to `ARCHITECTURE.md`, `TODO.md`, `docs/specs/requirements/**`, or runtime verification scripts in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/arch_fourth_pass'; packets = [('P00', 'bootstrap'), ('P01', 'unknown_plugin_preservation'), ('P02', 'subnode_contract_promotion'), ('P03', 'graph_mutation_validation_boundary'), ('P04', 'execution_runtime_dto_pipeline'), ('P05', 'shell_presenter_boundary'), ('P06', 'bridge_first_qml_contract_cleanup'), ('P07', 'verification_manifest_consolidation'), ('P08', 'docs_traceability_closeout')]; required = [packet_dir / 'ARCH_FOURTH_PASS_MANIFEST.md', packet_dir / 'ARCH_FOURTH_PASS_STATUS.md']; required += [packet_dir / f'ARCH_FOURTH_PASS_{code}_{slug}.md' for code, slug in packets]; required += [packet_dir / f'ARCH_FOURTH_PASS_{code}_{slug}_PROMPT.md' for code, slug in packets]; missing = [str(path) for path in required if not path.exists()]; status_text = (packet_dir / 'ARCH_FOURTH_PASS_STATUS.md').read_text(encoding='utf-8'); expectations = [('P00 Bootstrap', 'PASS'), ('P01 Unknown Plugin Preservation', 'PENDING'), ('P02 Subnode Contract Promotion', 'PENDING'), ('P03 Graph Mutation Validation Boundary', 'PENDING'), ('P04 Execution Runtime DTO Pipeline', 'PENDING'), ('P05 Shell Presenter Boundary', 'PENDING'), ('P06 Bridge-First QML Contract Cleanup', 'PENDING'), ('P07 Verification Manifest Consolidation', 'PENDING'), ('P08 Docs And Traceability Closeout', 'PENDING')]; bad_status = [f'{label}:{expected}' for label, expected in expectations if f'| {label} |' not in status_text or f'| {expected} |' not in next((line for line in status_text.splitlines() if f'| {label} |' in line), '')]; index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); refs = ['ARCH_FOURTH_PASS Work Packet Manifest', 'ARCH_FOURTH_PASS Status Ledger']; missing_refs = [ref for ref in refs if ref not in index_text]; ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'ARCH_FOURTH_PASS_MANIFEST.md')], capture_output=True, text=True); verdict = 'MISSING: ' + ', '.join(missing) if missing else 'STATUS_MISMATCH: ' + ', '.join(bad_status) if bad_status else 'INDEX_MISSING: ' + ', '.join(missing_refs) if missing_refs else 'ARCH_FOURTH_PASS_DOCS_IGNORED' if ignored.returncode == 0 else 'ARCH_FOURTH_PASS_P00_FILE_GATE_PASS'; print(verdict); sys.exit(0 if verdict == 'ARCH_FOURTH_PASS_P00_FILE_GATE_PASS' else 1)"`

## Review Gate
- `none`

## Expected Artifacts
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_MANIFEST.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_STATUS.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P00_bootstrap.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P01_unknown_plugin_preservation.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P01_unknown_plugin_preservation_PROMPT.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P02_subnode_contract_promotion.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P02_subnode_contract_promotion_PROMPT.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P03_graph_mutation_validation_boundary.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P03_graph_mutation_validation_boundary_PROMPT.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P04_execution_runtime_dto_pipeline.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P04_execution_runtime_dto_pipeline_PROMPT.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P05_shell_presenter_boundary.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P05_shell_presenter_boundary_PROMPT.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P06_bridge_first_qml_contract_cleanup.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P06_bridge_first_qml_contract_cleanup_PROMPT.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P07_verification_manifest_consolidation.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P07_verification_manifest_consolidation_PROMPT.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P08_docs_traceability_closeout.md`
- `docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_P08_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `ARCH_FOURTH_PASS_P00_FILE_GATE_PASS`.
- `ARCH_FOURTH_PASS_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only packet-owned modified paths are `.gitignore` if required, `docs/specs/INDEX.md`, and the new `arch_fourth_pass` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `ARCH_FOURTH_PASS_MANIFEST.md`, `ARCH_FOURTH_PASS_STATUS.md`, and `ARCH_FOURTH_PASS_P01_unknown_plugin_preservation.md` before editing code.
