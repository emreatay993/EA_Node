# ARCH_THIRD_PASS P00: Bootstrap

## Objective
- Establish the `ARCH_THIRD_PASS` packet set, initialize the status ledger, register the docs in the canonical spec index, and add the narrow `.gitignore` exception required to track this new packet directory.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `arch_third_pass` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only for the narrow `docs/specs/work_packets/arch_third_pass/` tracking exception
- `docs/specs/work_packets/arch_third_pass/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_third_pass/**`

## Required Behavior
- Create `docs/specs/work_packets/arch_third_pass/`.
- Add the narrow `.gitignore` exception required so the new packet docs are not ignored by git.
- Add `ARCH_THIRD_PASS_MANIFEST.md` and `ARCH_THIRD_PASS_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P08` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `ARCH_THIRD_PASS` manifest and status ledger.
- Mark `P00` as `PASS` in `ARCH_THIRD_PASS_STATUS.md` and leave `P01` through `P08` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, and fresh-thread prompt shell in the manifest.
- Make no runtime, source, or test changes outside the documentation/bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to `ARCHITECTURE.md`, `TODO.md`, `docs/specs/requirements/**`, or runtime verification scripts in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/arch_third_pass'; packets = [('P00', 'bootstrap'), ('P01', 'shell_composition_root'), ('P02', 'workspace_library_capabilities'), ('P03', 'bridge_first_shell_canvas'), ('P04', 'scene_mutation_contracts'), ('P05', 'passive_media_bridge_cleanup'), ('P06', 'execution_worker_runtime'), ('P07', 'validation_persistence_centralization'), ('P08', 'verification_traceability')]; required = [packet_dir / 'ARCH_THIRD_PASS_MANIFEST.md', packet_dir / 'ARCH_THIRD_PASS_STATUS.md']; required += [packet_dir / f'ARCH_THIRD_PASS_{code}_{slug}.md' for code, slug in packets]; required += [packet_dir / f'ARCH_THIRD_PASS_{code}_{slug}_PROMPT.md' for code, slug in packets]; missing = [str(path) for path in required if not path.exists()]; status_text = (packet_dir / 'ARCH_THIRD_PASS_STATUS.md').read_text(encoding='utf-8'); expectations = [('P00 Bootstrap', 'PASS'), ('P01 Shell Composition Root', 'PENDING'), ('P02 Workspace Library Capabilities', 'PENDING'), ('P03 Bridge-First Shell And Canvas Roots', 'PENDING'), ('P04 Scene Mutation Contracts', 'PENDING'), ('P05 Passive Media Bridge Cleanup', 'PENDING'), ('P06 Execution Worker Runtime', 'PENDING'), ('P07 Validation And Persistence Centralization', 'PENDING'), ('P08 Verification And Traceability', 'PENDING')]; bad_status = [f'{label}:{expected}' for label, expected in expectations if f'| {label} |' not in status_text or f'| {expected} |' not in next((line for line in status_text.splitlines() if f'| {label} |' in line), '')]; index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); refs = ['ARCH_THIRD_PASS Work Packet Manifest', 'ARCH_THIRD_PASS Status Ledger']; missing_refs = [ref for ref in refs if ref not in index_text]; ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'ARCH_THIRD_PASS_MANIFEST.md')], capture_output=True, text=True); verdict = 'MISSING: ' + ', '.join(missing) if missing else 'STATUS_MISMATCH: ' + ', '.join(bad_status) if bad_status else 'INDEX_MISSING: ' + ', '.join(missing_refs) if missing_refs else 'ARCH_THIRD_PASS_DOCS_IGNORED' if ignored.returncode == 0 else 'ARCH_THIRD_PASS_P00_FILE_GATE_PASS'; print(verdict); sys.exit(0 if verdict == 'ARCH_THIRD_PASS_P00_FILE_GATE_PASS' else 1)"`

## Review Gate
- `none`

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_MANIFEST.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_STATUS.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P00_bootstrap.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P01_shell_composition_root.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P01_shell_composition_root_PROMPT.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P02_workspace_library_capabilities.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P02_workspace_library_capabilities_PROMPT.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P03_bridge_first_shell_canvas.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P03_bridge_first_shell_canvas_PROMPT.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P04_scene_mutation_contracts.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P04_scene_mutation_contracts_PROMPT.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P05_passive_media_bridge_cleanup.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P05_passive_media_bridge_cleanup_PROMPT.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P06_execution_worker_runtime.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P06_execution_worker_runtime_PROMPT.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P07_validation_persistence_centralization.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P07_validation_persistence_centralization_PROMPT.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P08_verification_traceability.md`
- `docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_P08_verification_traceability_PROMPT.md`

## Acceptance Criteria
- The verification command returns `ARCH_THIRD_PASS_P00_FILE_GATE_PASS`.
- `ARCH_THIRD_PASS_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only packet-owned modified paths are `.gitignore`, the new `arch_third_pass` packet docs, and `docs/specs/INDEX.md`.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `ARCH_THIRD_PASS_MANIFEST.md`, `ARCH_THIRD_PASS_STATUS.md`, and `ARCH_THIRD_PASS_P01_shell_composition_root.md` before editing code.
