# PLUGIN_PACKAGE_CONTRACT P00: Bootstrap

## Objective
- Establish the `PLUGIN_PACKAGE_CONTRACT` packet set, initialize the status ledger, register the docs in the canonical spec index, and add the narrow `.gitignore` exception required to track this new packet directory.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `plugin_package_contract` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only for the narrow `docs/specs/work_packets/plugin_package_contract/` tracking exception
- `docs/specs/work_packets/plugin_package_contract/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/plugin_package_contract/**`

## Required Behavior
- Create `docs/specs/work_packets/plugin_package_contract/`.
- Add the narrow `.gitignore` exception required so the new packet docs are not ignored by git.
- Add `PLUGIN_PACKAGE_CONTRACT_MANIFEST.md` and `PLUGIN_PACKAGE_CONTRACT_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P05` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `PLUGIN_PACKAGE_CONTRACT` manifest and status ledger.
- Mark `P00` as `PASS` in `PLUGIN_PACKAGE_CONTRACT_STATUS.md` and leave `P01` through `P05` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, and fresh-thread prompt shell in the manifest.
- Make no runtime, source, or test changes outside the documentation/bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to `README.md`, `ARCHITECTURE.md`, `docs/GETTING_STARTED.md`, `docs/specs/requirements/**`, or runtime verification scripts in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/plugin_package_contract'; packets = [('P00', 'bootstrap'), ('P01', 'loader_directory_contract'), ('P02', 'package_import_layout'), ('P03', 'package_export_contract'), ('P04', 'shell_package_workflows'), ('P05', 'docs_traceability')]; required = [packet_dir / 'PLUGIN_PACKAGE_CONTRACT_MANIFEST.md', packet_dir / 'PLUGIN_PACKAGE_CONTRACT_STATUS.md']; required += [packet_dir / f'PLUGIN_PACKAGE_CONTRACT_{code}_{slug}.md' for code, slug in packets]; required += [packet_dir / f'PLUGIN_PACKAGE_CONTRACT_{code}_{slug}_PROMPT.md' for code, slug in packets]; missing = [str(path) for path in required if not path.exists()]; status_text = (packet_dir / 'PLUGIN_PACKAGE_CONTRACT_STATUS.md').read_text(encoding='utf-8'); expectations = [('P00 Bootstrap', 'PASS'), ('P01 Loader Directory Contract', 'PENDING'), ('P02 Package Import Layout', 'PENDING'), ('P03 Package Export Contract', 'PENDING'), ('P04 Shell Package Workflows', 'PENDING'), ('P05 Docs And Traceability', 'PENDING')]; bad_status = [f'{label}:{expected}' for label, expected in expectations if f'| {label} |' not in status_text or f'| {expected} |' not in next((line for line in status_text.splitlines() if f'| {label} |' in line), '')]; index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); refs = ['PLUGIN_PACKAGE_CONTRACT Work Packet Manifest', 'PLUGIN_PACKAGE_CONTRACT Status Ledger']; missing_refs = [ref for ref in refs if ref not in index_text]; ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'PLUGIN_PACKAGE_CONTRACT_MANIFEST.md')], capture_output=True, text=True); verdict = 'MISSING: ' + ', '.join(missing) if missing else 'STATUS_MISMATCH: ' + ', '.join(bad_status) if bad_status else 'INDEX_MISSING: ' + ', '.join(missing_refs) if missing_refs else 'PLUGIN_PACKAGE_CONTRACT_DOCS_IGNORED' if ignored.returncode == 0 else 'PLUGIN_PACKAGE_CONTRACT_P00_FILE_GATE_PASS'; print(verdict); sys.exit(0 if verdict == 'PLUGIN_PACKAGE_CONTRACT_P00_FILE_GATE_PASS' else 1)`"

## Review Gate
- none

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_MANIFEST.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P00_bootstrap.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P01_loader_directory_contract.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P01_loader_directory_contract_PROMPT.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P02_package_import_layout.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P02_package_import_layout_PROMPT.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P03_package_export_contract.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P03_package_export_contract_PROMPT.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P04_shell_package_workflows.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P04_shell_package_workflows_PROMPT.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P05_docs_traceability.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_P05_docs_traceability_PROMPT.md`

## Acceptance Criteria
- The verification command returns `PLUGIN_PACKAGE_CONTRACT_P00_FILE_GATE_PASS`.
- `PLUGIN_PACKAGE_CONTRACT_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only packet-owned modified paths are `.gitignore`, the new `plugin_package_contract` packet docs, and `docs/specs/INDEX.md`.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `PLUGIN_PACKAGE_CONTRACT_MANIFEST.md`, `PLUGIN_PACKAGE_CONTRACT_STATUS.md`, and `PLUGIN_PACKAGE_CONTRACT_P01_loader_directory_contract.md` before editing code.
