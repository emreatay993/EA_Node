# P04 Save Promotion Prune Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/project-managed-files/p04-save-promotion-prune`
- Commit Owner: `worker`
- Commit SHA: `dd9089a7ca129cbac80c94bbd2f90f9d1a42dfed`
- Changed Files: `docs/specs/work_packets/project_managed_files/P04_save_promotion_prune_WRAPUP.md`, `ea_node_editor/persistence/artifact_store.py`, `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/persistence/serializer.py`, `ea_node_editor/ui/shell/controllers/project_session_controller.py`, `tests/serializer/round_trip_cases.py`, `tests/test_project_artifact_store.py`, `tests/test_shell_project_session_controller.py`
- Artifacts Produced: `docs/specs/work_packets/project_managed_files/P04_save_promotion_prune_WRAPUP.md`, `ea_node_editor/persistence/artifact_store.py`, `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/persistence/serializer.py`, `ea_node_editor/ui/shell/controllers/project_session_controller.py`, `tests/serializer/round_trip_cases.py`, `tests/test_project_artifact_store.py`, `tests/test_shell_project_session_controller.py`
- Explicit `Save` now scans the persistent project document for managed and staged refs, promotes only the still-referenced staged payloads into `<project-stem>.data/`, rewrites promoted refs from `artifact-stage://...` to `artifact://...`, preserves replace-in-place semantics for existing managed artifact ids, removes unreferenced permanent managed files, and clears temp staging-root hints once save no longer depends on them.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py tests/test_shell_project_session_controller.py tests/serializer/round_trip_cases.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_serializer.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Too soon for manual testing.

- This packet changes explicit `Save` semantics only after a project already contains staged managed refs, but the current branch still has no user-facing import or stored-output flow that creates those refs from the shell UI.
- Manual testing becomes worthwhile once a later packet exposes managed imports or stored outputs that can be staged and then saved without developer scaffolding.

## Residual Risks

- Save-time promotion and prune behavior is still validated through automated persistence and shell tests only until later packets expose user-facing managed-import or stored-output producers.
- If a staged ref is still referenced at save time but its payload is already missing, this packet leaves that staged ref unresolved rather than inventing a managed replacement; later file-issue UX packets still need to surface and repair that state cleanly.

## Ready for Integration

- Yes: the packet stays inside scope, preserves the staged-to-managed contract from earlier waves, and passes the required verification command, review gate, and serializer follow-up coverage.
