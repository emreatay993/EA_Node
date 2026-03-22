# COMMENT_BACKDROP P00: Bootstrap

## Objective
- Establish the `COMMENT_BACKDROP` packet set, initialize the status ledger, register the docs in the canonical spec index, and add the required narrow `.gitignore` exception so the new packet docs are tracked.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `comment_backdrop` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/comment_backdrop/*`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/comment_backdrop/**`

## Required Behavior
- Create `docs/specs/work_packets/comment_backdrop/`.
- Add `COMMENT_BACKDROP_MANIFEST.md` and `COMMENT_BACKDROP_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P08` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `COMMENT_BACKDROP` manifest and status ledger.
- Add the narrow `.gitignore` exception required for `docs/specs/work_packets/comment_backdrop/`.
- Mark `P00` as `PASS` in `COMMENT_BACKDROP_STATUS.md` and leave `P01` through `P08` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, review gates, expected artifacts, and fresh-thread prompt shell in the packet docs.
- Make no runtime, source, or test changes outside the documentation and bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to runtime verification scripts, packet-external manifests, or requirements docs in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/comment_backdrop'; packets = [('P00', 'bootstrap', 'P00 Bootstrap', 'PASS'), ('P01', 'catalog_surface_contract', 'P01 Catalog + Surface Contract', 'PENDING'), ('P02', 'backdrop_layer_bridge_split', 'P02 Backdrop Layer + Bridge Split', 'PENDING'), ('P03', 'geometry_membership_wrap_selection', 'P03 Geometry Membership + Wrap Selection', 'PENDING'), ('P04', 'drag_resize_nested_motion', 'P04 Drag/Resize + Nested Motion', 'PENDING'), ('P05', 'collapse_boundary_edge_routing', 'P05 Collapse + Boundary Edge Routing', 'PENDING'), ('P06', 'editing_shell_creation_affordances', 'P06 Editing + Shell Creation Affordances', 'PENDING'), ('P07', 'clipboard_delete_load_recompute', 'P07 Clipboard + Delete + Load Recompute', 'PENDING'), ('P08', 'docs_traceability_closeout', 'P08 Docs + Traceability Closeout', 'PENDING')]; required = [packet_dir / 'COMMENT_BACKDROP_MANIFEST.md', packet_dir / 'COMMENT_BACKDROP_STATUS.md']; required += [packet_dir / f'COMMENT_BACKDROP_{code}_{slug}.md' for code, slug, _label, _status in packets]; required += [packet_dir / f'COMMENT_BACKDROP_{code}_{slug}_PROMPT.md' for code, slug, _label, _status in packets]; missing = [str(path) for path in required if not path.exists()]; status_text = (packet_dir / 'COMMENT_BACKDROP_STATUS.md').read_text(encoding='utf-8'); lines = status_text.splitlines(); bad_status = []; [bad_status.append(f'{label}:{expected}') for _code, _slug, label, expected in packets if f'| {label} |' not in status_text or f'| {expected} |' not in next((line for line in lines if f'| {label} |' in line), '')]; index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); refs = ['COMMENT_BACKDROP Work Packet Manifest', 'COMMENT_BACKDROP Status Ledger']; missing_refs = [ref for ref in refs if ref not in index_text]; ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'COMMENT_BACKDROP_MANIFEST.md')], capture_output=True, text=True); verdict = 'MISSING: ' + ', '.join(missing) if missing else 'STATUS_MISMATCH: ' + ', '.join(bad_status) if bad_status else 'INDEX_MISSING: ' + ', '.join(missing_refs) if missing_refs else 'COMMENT_BACKDROP_DOCS_IGNORED' if ignored.returncode == 0 else 'COMMENT_BACKDROP_P00_FILE_GATE_PASS'; print(verdict); sys.exit(0 if verdict == 'COMMENT_BACKDROP_P00_FILE_GATE_PASS' else 1)"`

## Review Gate
- `none`

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_MANIFEST.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P00_bootstrap.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P01_catalog_surface_contract.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P01_catalog_surface_contract_PROMPT.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P02_backdrop_layer_bridge_split.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P02_backdrop_layer_bridge_split_PROMPT.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P03_geometry_membership_wrap_selection.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P03_geometry_membership_wrap_selection_PROMPT.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P04_drag_resize_nested_motion.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P04_drag_resize_nested_motion_PROMPT.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P05_collapse_boundary_edge_routing.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P05_collapse_boundary_edge_routing_PROMPT.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P06_editing_shell_creation_affordances.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P06_editing_shell_creation_affordances_PROMPT.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P07_clipboard_delete_load_recompute.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P07_clipboard_delete_load_recompute_PROMPT.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P08_docs_traceability_closeout.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_P08_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria
- The verification command returns `COMMENT_BACKDROP_P00_FILE_GATE_PASS`.
- `COMMENT_BACKDROP_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only packet-owned modified paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `comment_backdrop` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `COMMENT_BACKDROP_MANIFEST.md`, `COMMENT_BACKDROP_STATUS.md`, and `COMMENT_BACKDROP_P01_catalog_surface_contract.md` before editing code.
