# ARCH_SIXTH_PASS P00: Bootstrap

## Objective
- Establish the `ARCH_SIXTH_PASS` packet set, initialize the status ledger, register the docs in the canonical spec index, and add the required narrow `.gitignore` exception so the new packet docs are tracked.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `arch_sixth_pass` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_sixth_pass/*`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_sixth_pass/**`

## Required Behavior
- Create `docs/specs/work_packets/arch_sixth_pass/`.
- Add `ARCH_SIXTH_PASS_MANIFEST.md` and `ARCH_SIXTH_PASS_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P12` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `ARCH_SIXTH_PASS` manifest and status ledger.
- Add the narrow `.gitignore` exception required for `docs/specs/work_packets/arch_sixth_pass/`.
- Mark `P00` as `PASS` in `ARCH_SIXTH_PASS_STATUS.md` and leave `P01` through `P12` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, review gates, expected artifacts, and fresh-thread prompt shell in the packet docs.
- Make no runtime, source, or test changes outside the documentation and bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to runtime verification scripts, packet-external manifests, or requirements docs in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/arch_sixth_pass'; packets = [('P00', 'bootstrap', 'P00 Bootstrap', 'PASS'), ('P01', 'shell_bootstrap_contract', 'P01 Shell Bootstrap Contract', 'PENDING'), ('P02', 'shell_window_facade_contraction', 'P02 ShellWindow Facade Contraction', 'PENDING'), ('P03', 'shell_contract_hardening', 'P03 Shell Contract Hardening', 'PENDING'), ('P04', 'canvas_contract_completion', 'P04 Canvas Contract Completion', 'PENDING'), ('P05', 'graph_authoring_transaction_core', 'P05 Graph Authoring Transaction Core', 'PENDING'), ('P06', 'workspace_state_history_boundary', 'P06 Workspace State And History Boundary', 'PENDING'), ('P07', 'workspace_lifecycle_authority', 'P07 Workspace Lifecycle Authority', 'PENDING'), ('P08', 'execution_boundary_hardening', 'P08 Execution Boundary Hardening', 'PENDING'), ('P09', 'persistence_overlay_ownership', 'P09 Persistence Overlay Ownership', 'PENDING'), ('P10', 'plugin_package_provenance_hardening', 'P10 Plugin Package Provenance Hardening', 'PENDING'), ('P11', 'shell_verification_lifecycle_hardening', 'P11 Shell Verification Lifecycle Hardening', 'PENDING'), ('P12', 'docs_traceability_closeout', 'P12 Docs And Traceability Closeout', 'PENDING')]; required = [packet_dir / 'ARCH_SIXTH_PASS_MANIFEST.md', packet_dir / 'ARCH_SIXTH_PASS_STATUS.md']; required += [packet_dir / f'ARCH_SIXTH_PASS_{code}_{slug}.md' for code, slug, _label, _status in packets]; required += [packet_dir / f'ARCH_SIXTH_PASS_{code}_{slug}_PROMPT.md' for code, slug, _label, _status in packets]; missing = [str(path) for path in required if not path.exists()]; status_text = (packet_dir / 'ARCH_SIXTH_PASS_STATUS.md').read_text(encoding='utf-8'); lines = status_text.splitlines(); bad_status = []; [bad_status.append(f'{label}:{expected}') for _code, _slug, label, expected in packets if f'| {label} |' not in status_text or f'| {expected} |' not in next((line for line in lines if f'| {label} |' in line), '')]; index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); refs = ['ARCH_SIXTH_PASS Work Packet Manifest', 'ARCH_SIXTH_PASS Status Ledger']; missing_refs = [ref for ref in refs if ref not in index_text]; ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'ARCH_SIXTH_PASS_MANIFEST.md')], capture_output=True, text=True); verdict = 'MISSING: ' + ', '.join(missing) if missing else 'STATUS_MISMATCH: ' + ', '.join(bad_status) if bad_status else 'INDEX_MISSING: ' + ', '.join(missing_refs) if missing_refs else 'ARCH_SIXTH_PASS_DOCS_IGNORED' if ignored.returncode == 0 else 'ARCH_SIXTH_PASS_P00_FILE_GATE_PASS'; print(verdict); sys.exit(0 if verdict == 'ARCH_SIXTH_PASS_P00_FILE_GATE_PASS' else 1)"`

## Review Gate
- `none`

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_MANIFEST.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P00_bootstrap.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P01_shell_bootstrap_contract.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P01_shell_bootstrap_contract_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P02_shell_window_facade_contraction.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P02_shell_window_facade_contraction_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P03_shell_contract_hardening.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P03_shell_contract_hardening_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P04_canvas_contract_completion.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P04_canvas_contract_completion_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P05_graph_authoring_transaction_core.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P05_graph_authoring_transaction_core_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P06_workspace_state_history_boundary.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P06_workspace_state_history_boundary_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P07_workspace_lifecycle_authority.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P07_workspace_lifecycle_authority_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P08_execution_boundary_hardening.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P08_execution_boundary_hardening_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P09_persistence_overlay_ownership.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P09_persistence_overlay_ownership_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P10_plugin_package_provenance_hardening.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P10_plugin_package_provenance_hardening_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P11_shell_verification_lifecycle_hardening.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P11_shell_verification_lifecycle_hardening_PROMPT.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P12_docs_traceability_closeout.md`
- `docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_P12_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `ARCH_SIXTH_PASS_P00_FILE_GATE_PASS`.
- `ARCH_SIXTH_PASS_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only packet-owned modified paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `arch_sixth_pass` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `ARCH_SIXTH_PASS_MANIFEST.md`, `ARCH_SIXTH_PASS_STATUS.md`, and `ARCH_SIXTH_PASS_P01_shell_bootstrap_contract.md` before editing code.
