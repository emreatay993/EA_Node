# P01 Unknown Plugin Preservation Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/arch-fourth-pass/p01-unknown-plugin-preservation`
- Commit Owner: `worker`
- Commit SHA: `3eb6c77512a7e6ed8c2c700d77ab4caaa4d7c6e7`
- Changed Files: `docs/specs/work_packets/arch_fourth_pass/P01_unknown_plugin_preservation_WRAPUP.md`, `ea_node_editor/graph/model.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/persistence/migration.py`, `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/persistence/serializer.py`, `tests/test_registry_validation.py`, `tests/test_serializer.py`, `tests/test_serializer_schema_migration.py`
- Artifacts Produced: `docs/specs/work_packets/arch_fourth_pass/P01_unknown_plugin_preservation_WRAPUP.md`

Added an unresolved-content sidecar on `WorkspaceData`, kept migration output lossless for unresolved node and mixed-edge payloads, and split the codec/serializer boundary into a runtime-safe document path plus an authored save path. Runtime documents now exclude unresolved nodes and edges from the executable graph while carrying an internal sidecar for autosave/session round trips, authored saves merge the preserved payloads back into `nodes` and `edges`, and live known nodes no longer retain dangling `parent_node_id` references to unresolved parents.

## Verification

- PASS: `./venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_serializer_schema_migration tests.test_registry_validation -v`
- PASS: `./venv/Scripts/python.exe -m unittest tests.test_serializer -v`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch with the default registry only, and use an `.sfe` project that contains at least one node whose `type_id` comes from a missing plugin plus at least one normal built-in node.
- Load/save preservation smoke: open the project, save it, then inspect the saved `.sfe`. Expected: the unresolved node and any edge attached to it are still present in the workspace `nodes` and `edges` arrays with their plugin-authored payload fields intact.
- Known-node sanity: reopen the saved project and confirm the registry-resolved nodes still load normally and valid known-node edges remain intact. Expected: known content behaves deterministically while the unresolved content is preserved only for round-trip persistence.
- Run smoke: if the project still contains a valid built-in execution path, run that workspace. Expected: the resolved graph still runs, unresolved nodes do not appear in the executable runtime graph, and edges attached to unresolved nodes do not fire.
- Missing-parent smoke: load a project where a built-in node was authored under a missing-plugin parent, then save the project and inspect the output. Expected: the live session shows the built-in node at top level instead of dangling under a missing parent, but the saved `.sfe` still restores the authored `parent_node_id` reference losslessly.

## Residual Risks

- `StartRunCommand.project_doc` payloads that bypass serializer/model hydration can still hand raw unresolved nodes directly to the worker/compiler path; this packet hardens the owned load, normalize, and save path, not the broader runtime DTO boundary.
- Preserved unresolved payloads are intentionally opaque sidecar data in the live model, so users still have no packet-owned UI affordance for inspecting or editing that preserved content until the missing plugin returns or a later packet addresses it.

## Ready for Integration

- Yes: unresolved plugin-authored nodes and connected edges now survive migration, normalization, and save without schema changes, and the packet verification plus review gate both passed in the project venv.
