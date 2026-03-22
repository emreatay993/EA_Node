# PORT_LABEL_VISIBILITY P00: Bootstrap

## Objective
- Establish the `PORT_LABEL_VISIBILITY` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and add the required narrow `.gitignore` exception so the new packet docs are tracked.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `port_label_visibility` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/port_label_visibility/*`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/port_label_visibility/**`

## Required Behavior
- Create `docs/specs/work_packets/port_label_visibility/`.
- Add `PORT_LABEL_VISIBILITY_MANIFEST.md` and `PORT_LABEL_VISIBILITY_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P04` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `PORT_LABEL_VISIBILITY` manifest and status ledger.
- Add the narrow `.gitignore` exception required for `docs/specs/work_packets/port_label_visibility/`.
- Mark `P00` as `PASS` in `PORT_LABEL_VISIBILITY_STATUS.md` and leave `P01` through `P04` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, review gates, expected artifacts, and fresh-thread prompt shell in the packet docs.
- Make no runtime, source, or test changes outside the documentation and bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to runtime verification scripts, packet-external manifests, or requirements docs in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/port_label_visibility'; packets = [('P00', 'bootstrap', 'P00 Bootstrap', 'PASS'), ('P01', 'preferences_bridge_contract', 'P01 Preferences + Bridge Contract', 'PENDING'), ('P02', 'shell_ui_toggle_sync', 'P02 Shell UI Toggle Sync', 'PENDING'), ('P03', 'standard_node_width_policy', 'P03 Standard Node Width Policy', 'PENDING'), ('P04', 'qml_label_presentation_rollout', 'P04 QML Label Presentation Rollout', 'PENDING')]; required = [packet_dir / 'PORT_LABEL_VISIBILITY_MANIFEST.md', packet_dir / 'PORT_LABEL_VISIBILITY_STATUS.md']; required += [packet_dir / f'PORT_LABEL_VISIBILITY_{code}_{slug}.md' for code, slug, _label, _status in packets]; required += [packet_dir / f'PORT_LABEL_VISIBILITY_{code}_{slug}_PROMPT.md' for code, slug, _label, _status in packets]; missing = [str(path) for path in required if not path.exists()]; status_text = (packet_dir / 'PORT_LABEL_VISIBILITY_STATUS.md').read_text(encoding='utf-8'); lines = status_text.splitlines(); bad_status = []; [bad_status.append(f'{label}:{expected}') for _code, _slug, label, expected in packets if f'| {label} |' not in status_text or f'| {expected} |' not in next((line for line in lines if f'| {label} |' in line), '')]; index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); refs = ['PORT_LABEL_VISIBILITY Work Packet Manifest', 'PORT_LABEL_VISIBILITY Status Ledger']; missing_refs = [ref for ref in refs if ref not in index_text]; ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'PORT_LABEL_VISIBILITY_MANIFEST.md')], capture_output=True, text=True); verdict = 'MISSING: ' + ', '.join(missing) if missing else 'STATUS_MISMATCH: ' + ', '.join(bad_status) if bad_status else 'INDEX_MISSING: ' + ', '.join(missing_refs) if missing_refs else 'PORT_LABEL_VISIBILITY_DOCS_IGNORED' if ignored.returncode == 0 else 'PORT_LABEL_VISIBILITY_P00_FILE_GATE_PASS'; print(verdict); sys.exit(0 if verdict == 'PORT_LABEL_VISIBILITY_P00_FILE_GATE_PASS' else 1)"`

## Review Gate
- `none`

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_MANIFEST.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_STATUS.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P00_bootstrap.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P01_preferences_bridge_contract.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P01_preferences_bridge_contract_PROMPT.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P02_shell_ui_toggle_sync.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P02_shell_ui_toggle_sync_PROMPT.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P03_standard_node_width_policy.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P03_standard_node_width_policy_PROMPT.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P04_qml_label_presentation_rollout.md`
- `docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_P04_qml_label_presentation_rollout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `PORT_LABEL_VISIBILITY_P00_FILE_GATE_PASS`.
- `PORT_LABEL_VISIBILITY_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only packet-owned modified paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `port_label_visibility` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `PORT_LABEL_VISIBILITY_MANIFEST.md`, `PORT_LABEL_VISIBILITY_STATUS.md`, and `PORT_LABEL_VISIBILITY_P01_preferences_bridge_contract.md` before editing code.
