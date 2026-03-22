# NODE_INLINE_TITLES P00: Bootstrap

## Objective
- Establish the `NODE_INLINE_TITLES` packet set, initialize the status ledger, register the docs in the canonical spec index, and add the required narrow `.gitignore` exception so the new packet docs are tracked.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `node_inline_titles` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/node_inline_titles/*`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/node_inline_titles/**`

## Required Behavior
- Create `docs/specs/work_packets/node_inline_titles/`.
- Add `NODE_INLINE_TITLES_MANIFEST.md` and `NODE_INLINE_TITLES_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P04` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `NODE_INLINE_TITLES` manifest and status ledger.
- Add the narrow `.gitignore` exception required for `docs/specs/work_packets/node_inline_titles/`.
- Mark `P00` as `PASS` in `NODE_INLINE_TITLES_STATUS.md` and leave `P01` through `P04` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, review gates, expected artifacts, and fresh-thread prompt shell in the packet docs.
- Make no runtime, source, or test changes outside the documentation and bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to runtime verification scripts, packet-external manifests, or requirements docs in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/node_inline_titles'; packets = [('P00', 'bootstrap', 'P00 Bootstrap', 'PASS'), ('P01', 'title_mutation_authority', 'P01 Title Mutation Authority', 'PENDING'), ('P02', 'shared_header_title_rollout', 'P02 Shared Header Title Rollout', 'PENDING'), ('P03', 'scoped_title_edit_integration', 'P03 Scoped Title Edit Integration', 'PENDING'), ('P04', 'docs_traceability_closeout', 'P04 Docs And Traceability Closeout', 'PENDING')]; required = [packet_dir / 'NODE_INLINE_TITLES_MANIFEST.md', packet_dir / 'NODE_INLINE_TITLES_STATUS.md']; required += [packet_dir / f'NODE_INLINE_TITLES_{code}_{slug}.md' for code, slug, _label, _status in packets]; required += [packet_dir / f'NODE_INLINE_TITLES_{code}_{slug}_PROMPT.md' for code, slug, _label, _status in packets]; missing = [str(path) for path in required if not path.exists()]; status_text = (packet_dir / 'NODE_INLINE_TITLES_STATUS.md').read_text(encoding='utf-8'); lines = status_text.splitlines(); bad_status = []; [bad_status.append(f'{label}:{expected}') for _code, _slug, label, expected in packets if f'| {label} |' not in status_text or f'| {expected} |' not in next((line for line in lines if f'| {label} |' in line), '')]; index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); refs = ['NODE_INLINE_TITLES Work Packet Manifest', 'NODE_INLINE_TITLES Status Ledger']; missing_refs = [ref for ref in refs if ref not in index_text]; ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'NODE_INLINE_TITLES_MANIFEST.md')], capture_output=True, text=True); verdict = 'MISSING: ' + ', '.join(missing) if missing else 'STATUS_MISMATCH: ' + ', '.join(bad_status) if bad_status else 'INDEX_MISSING: ' + ', '.join(missing_refs) if missing_refs else 'NODE_INLINE_TITLES_DOCS_IGNORED' if ignored.returncode == 0 else 'NODE_INLINE_TITLES_P00_FILE_GATE_PASS'; print(verdict); sys.exit(0 if verdict == 'NODE_INLINE_TITLES_P00_FILE_GATE_PASS' else 1)"`

## Review Gate
- `none`

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_MANIFEST.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_STATUS.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P00_bootstrap.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P01_title_mutation_authority.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P01_title_mutation_authority_PROMPT.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P02_shared_header_title_rollout.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P02_shared_header_title_rollout_PROMPT.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P03_scoped_title_edit_integration.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P03_scoped_title_edit_integration_PROMPT.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P04_docs_traceability_closeout.md`
- `docs/specs/work_packets/node_inline_titles/NODE_INLINE_TITLES_P04_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `NODE_INLINE_TITLES_P00_FILE_GATE_PASS`.
- `NODE_INLINE_TITLES_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only packet-owned modified paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `node_inline_titles` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `NODE_INLINE_TITLES_MANIFEST.md`, `NODE_INLINE_TITLES_STATUS.md`, and `NODE_INLINE_TITLES_P01_title_mutation_authority.md` before editing code.
