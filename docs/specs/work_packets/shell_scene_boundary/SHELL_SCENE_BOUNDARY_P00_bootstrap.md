# SHELL_SCENE_BOUNDARY P00: Bootstrap

## Objective
- Establish the `SHELL_SCENE_BOUNDARY` packet set, initialize the status ledger, register the docs in the canonical spec index, and add the narrow `.gitignore` exception needed to track this new packet directory.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `shell_scene_boundary` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only for the narrow `docs/specs/work_packets/shell_scene_boundary/` tracking exception
- `docs/specs/work_packets/shell_scene_boundary/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/shell_scene_boundary/**`

## Required Behavior
- Create `docs/specs/work_packets/shell_scene_boundary/`.
- Add `SHELL_SCENE_BOUNDARY_MANIFEST.md` and `SHELL_SCENE_BOUNDARY_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P10` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `SHELL_SCENE_BOUNDARY` manifest and status ledger.
- Add the narrow `.gitignore` exception required so the new packet docs are not ignored by git.
- Mark `P00` as `PASS` in `SHELL_SCENE_BOUNDARY_STATUS.md` and leave `P01` through `P10` as `PENDING`.
- Encode the execution waves, locked defaults, conservative write scopes, and fresh-thread prompt shell in the manifest.
- Make no runtime, source, or test changes outside the documentation/bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes to `TODO.md`, `ARCHITECTURE.md`, or requirements docs in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -c "from pathlib import Path; import subprocess, sys; root = Path('.'); packet_dir = root / 'docs/specs/work_packets/shell_scene_boundary'; required = [packet_dir / 'SHELL_SCENE_BOUNDARY_MANIFEST.md', packet_dir / 'SHELL_SCENE_BOUNDARY_STATUS.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P00_bootstrap.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P00_bootstrap_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P01_settings_defaults_boundary.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P01_settings_defaults_boundary_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P02_qml_context_bootstrap.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P02_qml_context_bootstrap_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P03_shell_library_search_bridge.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P03_shell_library_search_bridge_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P04_shell_workspace_run_bridge.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P04_shell_workspace_run_bridge_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P05_shell_inspector_bridge.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P05_shell_inspector_bridge_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P06_graph_canvas_boundary_bridge.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P06_graph_canvas_boundary_bridge_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P07_graph_scene_scope_selection_split.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P07_graph_scene_scope_selection_split_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P08_graph_scene_mutation_history_split.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P08_graph_scene_mutation_history_split_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P09_graph_scene_payload_builder_split.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P09_graph_scene_payload_builder_split_PROMPT.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P10_boundary_regression_docs.md', packet_dir / 'SHELL_SCENE_BOUNDARY_P10_boundary_regression_docs_PROMPT.md']; missing = [str(path) for path in required if not path.exists()]; status_lines = (packet_dir / 'SHELL_SCENE_BOUNDARY_STATUS.md').read_text(encoding='utf-8').splitlines(); expectations = [('P00 Bootstrap', 'PASS'), ('P01 Settings Defaults Boundary', 'PENDING'), ('P02 QML Context Bootstrap', 'PENDING'), ('P03 Shell Library Search Bridge', 'PENDING'), ('P04 Shell Workspace Run Bridge', 'PENDING'), ('P05 Shell Inspector Bridge', 'PENDING'), ('P06 GraphCanvas Boundary Bridge', 'PENDING'), ('P07 GraphScene Scope Selection Split', 'PENDING'), ('P08 GraphScene Mutation History Split', 'PENDING'), ('P09 GraphScene Payload Builder Split', 'PENDING'), ('P10 Boundary Regression Docs', 'PENDING')]; bad_status = []; \
for label, expected in expectations: \
    line = next((item for item in status_lines if f'| {label} |' in item), ''); \
    if f'| {expected} |' not in line: bad_status.append(f'{label}:{expected}'); \
index_text = (root / 'docs/specs/INDEX.md').read_text(encoding='utf-8'); \
manifest_ref = 'SHELL_SCENE_BOUNDARY Work Packet Manifest'; status_ref = 'SHELL_SCENE_BOUNDARY Status Ledger'; \
ignored = subprocess.run(['git', 'check-ignore', str(packet_dir / 'SHELL_SCENE_BOUNDARY_MANIFEST.md')], capture_output=True, text=True); \
if missing: print('MISSING: ' + ', '.join(missing)); sys.exit(1); \
if bad_status: print('STATUS_MISMATCH: ' + ', '.join(bad_status)); sys.exit(1); \
if manifest_ref not in index_text: print('INDEX_MISSING_SHELL_SCENE_BOUNDARY_MANIFEST'); sys.exit(1); \
if status_ref not in index_text: print('INDEX_MISSING_SHELL_SCENE_BOUNDARY_STATUS'); sys.exit(1); \
if ignored.returncode == 0: print('SHELL_SCENE_BOUNDARY_DOCS_IGNORED'); sys.exit(1); \
print('SHELL_SCENE_BOUNDARY_P00_FILE_GATE_PASS')"`

## Acceptance Criteria
- The verification command returns `SHELL_SCENE_BOUNDARY_P00_FILE_GATE_PASS`.
- The verification command confirms the new packet docs are not ignored by git.
- `SHELL_SCENE_BOUNDARY_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, the new `shell_scene_boundary` packet docs, and `docs/specs/INDEX.md`.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must read `SHELL_SCENE_BOUNDARY_MANIFEST.md`, `SHELL_SCENE_BOUNDARY_STATUS.md`, and `SHELL_SCENE_BOUNDARY_P01_settings_defaults_boundary.md` before editing code.
