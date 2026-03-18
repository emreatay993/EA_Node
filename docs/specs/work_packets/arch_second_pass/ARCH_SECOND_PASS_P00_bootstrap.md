# ARCH_SECOND_PASS P00: Bootstrap

## Objective
- Establish the `ARCH_SECOND_PASS` packet set, initialize the status ledger, register the docs in the canonical spec index, and add the narrow `.gitignore` exception required to track this new packet directory.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `arch_second_pass` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only for the narrow `docs/specs/work_packets/arch_second_pass/` tracking exception
- `docs/specs/work_packets/arch_second_pass/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/arch_second_pass/**`

## Required Behavior
- Create `docs/specs/work_packets/arch_second_pass/`.
- Add the narrow `.gitignore` exception required so the new packet docs are not ignored by git.
- Add `ARCH_SECOND_PASS_MANIFEST.md` and `ARCH_SECOND_PASS_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P08` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `ARCH_SECOND_PASS` manifest and status ledger.
- Mark `P00` as `PASS` in `ARCH_SECOND_PASS_STATUS.md` and leave `P01` through `P08` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, and fresh-thread prompt shell in the manifest.
- Make no runtime, source, or test changes outside the documentation/bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to `README.md`, `ARCHITECTURE.md`, `TODO.md`, or requirements docs in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/arch_second_pass'; packets = [('P00', 'bootstrap'), ('P01', 'shell_window_host_protocols'), ('P02', 'qml_bridge_contracts'), ('P03', 'graph_canvas_interaction_state'), ('P04', 'graph_node_host_split'), ('P05', 'surface_metrics_and_heavy_panes'), ('P06', 'graph_scene_core_contracts'), ('P07', 'persistence_workspace_ownership'), ('P08', 'verification_traceability_hardening')]; required = [packet_dir / 'ARCH_SECOND_PASS_MANIFEST.md', packet_dir / 'ARCH_SECOND_PASS_STATUS.md']; required += [packet_dir / f'ARCH_SECOND_PASS_{code}_{slug}.md' for code, slug in packets]; required += [packet_dir / f'ARCH_SECOND_PASS_{code}_{slug}_PROMPT.md' for code, slug in packets]; missing = [str(path) for path in required if not path.exists()]; status_text = (packet_dir / 'ARCH_SECOND_PASS_STATUS.md').read_text(encoding='utf-8'); expectations = [('P00 Bootstrap', 'PASS'), ('P01 ShellWindow Host Protocols', 'PENDING'), ('P02 QML Bridge Contracts', 'PENDING'), ('P03 GraphCanvas Interaction State', 'PENDING'), ('P04 GraphNodeHost Split', 'PENDING'), ('P05 Surface Metrics And Heavy Panes', 'PENDING'), ('P06 Graph Scene Core Contracts', 'PENDING'), ('P07 Persistence Workspace Ownership', 'PENDING'), ('P08 Verification Traceability Hardening', 'PENDING')]; bad_status = [f'{label}:{expected}' for label, expected in expectations if f'| {label} |' not in status_text or f'| {expected} |' not in next((line for line in status_text.splitlines() if f'| {label} |' in line), '')]; index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); refs = ['ARCH_SECOND_PASS Work Packet Manifest', 'ARCH_SECOND_PASS Status Ledger']; missing_refs = [ref for ref in refs if ref not in index_text]; ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'ARCH_SECOND_PASS_MANIFEST.md')], capture_output=True, text=True); if missing: print('MISSING: ' + ', '.join(missing)); sys.exit(1); if bad_status: print('STATUS_MISMATCH: ' + ', '.join(bad_status)); sys.exit(1); if missing_refs: print('INDEX_MISSING: ' + ', '.join(missing_refs)); sys.exit(1); if ignored.returncode == 0: print('ARCH_SECOND_PASS_DOCS_IGNORED'); sys.exit(1); print('ARCH_SECOND_PASS_P00_FILE_GATE_PASS')"`

## Acceptance Criteria
- The verification command returns `ARCH_SECOND_PASS_P00_FILE_GATE_PASS`.
- `ARCH_SECOND_PASS_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, the new `arch_second_pass` packet docs, and `docs/specs/INDEX.md`.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `ARCH_SECOND_PASS_MANIFEST.md`, `ARCH_SECOND_PASS_STATUS.md`, and `ARCH_SECOND_PASS_P01_shell_window_host_protocols.md` before editing code.
