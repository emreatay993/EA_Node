# ARCH_FIFTH_PASS P00: Bootstrap

## Objective
- Establish the `ARCH_FIFTH_PASS` packet set, initialize the status ledger, register the docs in the canonical spec index, and add the required narrow `.gitignore` exception so the new packet docs are tracked.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `arch_fifth_pass` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_fifth_pass/*`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_fifth_pass/**`

## Required Behavior
- Create `docs/specs/work_packets/arch_fifth_pass/`.
- Add `ARCH_FIFTH_PASS_MANIFEST.md` and `ARCH_FIFTH_PASS_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P13` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `ARCH_FIFTH_PASS` manifest and status ledger.
- Add the narrow `.gitignore` exception required for `docs/specs/work_packets/arch_fifth_pass/`.
- Mark `P00` as `PASS` in `ARCH_FIFTH_PASS_STATUS.md` and leave `P01` through `P13` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, review gates, expected artifacts, and fresh-thread prompt shell in the packet docs.
- Make no runtime, source, or test changes outside the documentation/bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to runtime verification scripts, packet-external manifests, or requirements docs in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/arch_fifth_pass'; packets = [('P00', 'bootstrap', 'P00 Bootstrap', 'PASS'), ('P01', 'startup_preferences_boundary', 'P01 Startup And Preferences Boundary', 'PENDING'), ('P02', 'shell_composition_root', 'P02 Shell Composition Root', 'PENDING'), ('P03', 'shell_controller_surface_split', 'P03 Shell Controller Surface Split', 'PENDING'), ('P04', 'bridge_contract_foundation', 'P04 Bridge Contract Foundation', 'PENDING'), ('P05', 'bridge_first_qml_migration', 'P05 Bridge-First QML Migration', 'PENDING'), ('P06', 'authoring_mutation_service_foundation', 'P06 Authoring Mutation Service Foundation', 'PENDING'), ('P07', 'authoring_mutation_completion_history', 'P07 Authoring Mutation Completion And History', 'PENDING'), ('P08', 'current_schema_persistence_boundary', 'P08 Current-Schema Persistence Boundary', 'PENDING'), ('P09', 'runtime_snapshot_execution_pipeline', 'P09 Runtime Snapshot Execution Pipeline', 'PENDING'), ('P10', 'plugin_descriptor_package_contract', 'P10 Plugin Descriptor And Package Contract', 'PENDING'), ('P11', 'regression_suite_modularization', 'P11 Regression Suite Modularization', 'PENDING'), ('P12', 'verification_manifest_traceability', 'P12 Verification Manifest And Traceability', 'PENDING'), ('P13', 'docs_traceability_closeout', 'P13 Docs And Traceability Closeout', 'PENDING')]; required = [packet_dir / 'ARCH_FIFTH_PASS_MANIFEST.md', packet_dir / 'ARCH_FIFTH_PASS_STATUS.md']; required += [packet_dir / f'ARCH_FIFTH_PASS_{code}_{slug}.md' for code, slug, _label, _status in packets]; required += [packet_dir / f'ARCH_FIFTH_PASS_{code}_{slug}_PROMPT.md' for code, slug, _label, _status in packets]; missing = [str(path) for path in required if not path.exists()]; status_text = (packet_dir / 'ARCH_FIFTH_PASS_STATUS.md').read_text(encoding='utf-8'); bad_status = []; lines = status_text.splitlines(); [bad_status.append(f'{label}:{expected}') for _code, _slug, label, expected in packets if f'| {label} |' not in status_text or f'| {expected} |' not in next((line for line in lines if f'| {label} |' in line), '')]; index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); refs = ['ARCH_FIFTH_PASS Work Packet Manifest', 'ARCH_FIFTH_PASS Status Ledger']; missing_refs = [ref for ref in refs if ref not in index_text]; ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'ARCH_FIFTH_PASS_MANIFEST.md')], capture_output=True, text=True); verdict = 'MISSING: ' + ', '.join(missing) if missing else 'STATUS_MISMATCH: ' + ', '.join(bad_status) if bad_status else 'INDEX_MISSING: ' + ', '.join(missing_refs) if missing_refs else 'ARCH_FIFTH_PASS_DOCS_IGNORED' if ignored.returncode == 0 else 'ARCH_FIFTH_PASS_P00_FILE_GATE_PASS'; print(verdict); sys.exit(0 if verdict == 'ARCH_FIFTH_PASS_P00_FILE_GATE_PASS' else 1)"`

## Review Gate
- `none`

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_MANIFEST.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P00_bootstrap.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P01_startup_preferences_boundary.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P01_startup_preferences_boundary_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P02_shell_composition_root.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P02_shell_composition_root_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P03_shell_controller_surface_split.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P03_shell_controller_surface_split_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P04_bridge_contract_foundation.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P04_bridge_contract_foundation_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P05_bridge_first_qml_migration.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P05_bridge_first_qml_migration_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P06_authoring_mutation_service_foundation.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P06_authoring_mutation_service_foundation_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P07_authoring_mutation_completion_history.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P07_authoring_mutation_completion_history_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P08_current_schema_persistence_boundary.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P08_current_schema_persistence_boundary_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P09_runtime_snapshot_execution_pipeline.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P09_runtime_snapshot_execution_pipeline_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P10_plugin_descriptor_package_contract.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P10_plugin_descriptor_package_contract_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P11_regression_suite_modularization.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P11_regression_suite_modularization_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P12_verification_manifest_traceability.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P12_verification_manifest_traceability_PROMPT.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P13_docs_traceability_closeout.md`
- `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_P13_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `ARCH_FIFTH_PASS_P00_FILE_GATE_PASS`.
- `ARCH_FIFTH_PASS_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only packet-owned modified paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `arch_fifth_pass` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `ARCH_FIFTH_PASS_MANIFEST.md`, `ARCH_FIFTH_PASS_STATUS.md`, and `ARCH_FIFTH_PASS_P01_startup_preferences_boundary.md` before editing code.
