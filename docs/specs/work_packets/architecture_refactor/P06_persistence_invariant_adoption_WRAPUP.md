# P06 Persistence Invariant Adoption Wrap-Up

## Implementation Summary

- Packet: `P06`
- Branch Label: `codex/architecture-refactor/p06-persistence-invariant-adoption`
- Commit Owner: `worker`
- Commit SHA: `6d00ea04305f1d4a8a7fe77fd1089e16c397f5c3`
- Changed Files: `ea_node_editor/graph/normalization.py`, `ea_node_editor/persistence/migration.py`, `ea_node_editor/persistence/overlay.py`, `ea_node_editor/persistence/project_codec.py`, `tests/serializer/schema_cases.py`, `tests/test_persistence_package_imports.py`, `tests/test_registry_validation.py`, `docs/specs/work_packets/architecture_refactor/P06_persistence_invariant_adoption_WRAPUP.md`
- Artifacts Produced: `ea_node_editor/graph/normalization.py`, `ea_node_editor/persistence/migration.py`, `ea_node_editor/persistence/overlay.py`, `ea_node_editor/persistence/project_codec.py`, `tests/serializer/schema_cases.py`, `tests/test_persistence_package_imports.py`, `tests/test_registry_validation.py`, `docs/specs/work_packets/architecture_refactor/P06_persistence_invariant_adoption_WRAPUP.md`
- Simplified `JsonProjectMigration` down to schema-shape normalization so registry-dependent node, port, and edge policy no longer diverges from the shared graph invariant kernel.
- Restored the compatibility fallback that fills missing known-node titles from the registry display name during both migration and codec reconstruction, and added a packet-owned regression test for that case.
- Added explicit `WorkspacePersistenceEnvelope`, `ProjectPersistenceEnvelope`, and `ProjectDocumentFlavor` contracts so runtime unresolved payloads and authored-node overrides are handled as named persistence-envelope data instead of an anonymous metadata sidecar.
- Moved codec reconstruction onto `normalize_project_for_registry()` and tightened the kernel’s load-time rules to preserve authored sparse properties, hidden-port filtering, and deterministic single-target edge acceptance through one shared authority.
- Updated the packet-owned serializer and import tests to assert the new runtime-envelope contract and guard the new helper types against import-cycle regressions.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_serializer_schema_migration.py tests/test_serializer.py tests/test_registry_validation.py tests/test_persistence_package_imports.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_serializer_schema_migration.py tests/test_persistence_package_imports.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

- Prerequisite: use this branch with a project that contains at least one missing-plugin node wired to known nodes, or create one from an existing regression fixture before launching the app.
- Load the project in the editor. Expected: the workspace opens without a persistence error, known nodes render normally, and invalid hidden/duplicate edges are not revived during load.
- Save the project, close it, and reopen it with the plugin still unavailable. Expected: the missing-plugin node and its unresolved edge payload remain recoverable after the round trip, while the live graph only keeps the valid resolved wiring.

## Residual Risks

- Runtime documents now store unresolved payloads under the explicit `_persistence_envelope` metadata contract; packet-owned decoding still accepts the legacy `_runtime_unresolved_workspaces` shape, but any out-of-scope consumer reading the old private key directly will need to move to the helper API.
- The shared kernel now preserves sparse property payloads by default during project normalization, so later packets should avoid reintroducing any registry-normalization path that silently fills absent persistence fields.

## Ready for Integration

- Yes: the packet-local implementation, review gate, and full verification command all passed, and the wrap-up records the substantive worker-owned commit SHA.
