# P01 Unknown Plugin Preservation Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/arch-fourth-pass/p01-unknown-plugin-preservation`
- Commit Owner: `emreatay993`
- Commit SHA: `813baace26c21ff05df1127618a0e0960803b117`
- Changed Files: `ea_node_editor/graph/model.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/persistence/migration.py`, `ea_node_editor/persistence/project_codec.py`, `tests/test_serializer.py`, `tests/test_serializer_schema_migration.py`, `tests/test_registry_validation.py`
- Artifacts Produced: `docs/specs/work_packets/arch_fourth_pass/P01_unknown_plugin_preservation_WRAPUP.md`

Added an unresolved-content sidecar on `WorkspaceData`, kept migration output lossless for unresolved node and mixed-edge payloads, and taught codec save/load to move unresolved plugin-authored content out of the live executable graph while merging it back into the authored document on save. Known-node normalization and deterministic serialization stay on the existing registry-resolved path, and the packet now has focused regressions for migration, normalization, and round-trip save behavior with missing plugins.

## Verification

- PASS: `./venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_serializer_schema_migration tests.test_registry_validation -v`
- PASS: `./venv/Scripts/python.exe -m unittest tests.test_serializer -v`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch with the default registry only, and use an `.sfe` project that contains at least one node whose `type_id` comes from a missing plugin plus at least one normal built-in node.
- Load/save preservation smoke: open the project, save it, then inspect the saved `.sfe`. Expected: the unresolved node and any edge attached to it are still present in the workspace `nodes` and `edges` arrays with their plugin-authored payload fields intact.
- Known-node sanity: reopen the saved project and confirm the registry-resolved nodes still load normally and valid known-node edges remain intact. Expected: known content behaves deterministically while the unresolved content is preserved only for round-trip persistence.
- Run smoke: if the project still contains a valid built-in execution path, run that workspace. Expected: the resolved graph still runs, and the preserved unresolved payload does not become an executable live node.

## Residual Risks

- `StartRunCommand.project_doc` payloads that bypass serializer/model hydration can still hand raw unresolved nodes directly to the worker/compiler path; this packet hardens the owned load, normalize, and save path, not the broader runtime DTO boundary.
- Preserved unresolved payloads are intentionally opaque sidecar data in the live model, so users still have no packet-owned UI affordance for inspecting or editing that preserved content until the missing plugin returns or a later packet addresses it.

## Ready for Integration

- Yes: unresolved plugin-authored nodes and connected edges now survive migration, normalization, and save without schema changes, and the packet verification plus review gate both passed in the project venv.
