# P08 Current Schema Persistence Boundary Wrap-Up

## Implementation Summary

- Packet: `P08`
- Branch Label: `codex/arch-fifth-pass/p08-current-schema-persistence-boundary`
- Commit Owner: `worker`
- Commit SHA: `16114adc6ff34d9bd261e51e464776ccad3819fa`
- Changed Files: `docs/specs/work_packets/arch_fifth_pass/P08_current_schema_persistence_boundary_WRAPUP.md`, `ea_node_editor/graph/model.py`, `ea_node_editor/persistence/migration.py`, `ea_node_editor/persistence/overlay.py`, `ea_node_editor/persistence/project_codec.py`, `tests/fixtures/persistence/schema_current_inconsistent.json`, `tests/fixtures/persistence/schema_current_minimal.json`, `tests/fixtures/persistence/schema_v0_minimal.json`, `tests/test_registry_validation.py`, `tests/test_serializer.py`, `tests/test_serializer_schema_migration.py`
- Artifacts Produced: `docs/specs/work_packets/arch_fifth_pass/P08_current_schema_persistence_boundary_WRAPUP.md`, `ea_node_editor/persistence/overlay.py`, `ea_node_editor/graph/model.py`, `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/persistence/migration.py`, `tests/test_serializer.py`, `tests/test_serializer_schema_migration.py`, `tests/test_registry_validation.py`, `tests/fixtures/persistence/schema_current_inconsistent.json`, `tests/fixtures/persistence/schema_current_minimal.json`

Introduced persistence-owned workspace overlay types for unresolved node/edge payloads and authored node overrides, then moved `WorkspaceData` to compatibility properties backed by that sidecar so unresolved persistence state no longer lives as dataclass-owned live-model fields. Updated the packet-owned codec paths to use the overlay boundary directly while preserving current-schema unresolved round-trip behavior, and simplified migration to reject pre-current-schema documents instead of carrying packet-owned legacy upgrade branches. The serializer and registry-validation coverage now assert the current-schema-only contract explicitly, including the compatibility property surface and the replacement of legacy schema fixtures with current-schema persistence fixtures.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_registry_validation.py -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: start the application from `codex/arch-fifth-pass/p08-current-schema-persistence-boundary` and use a current-schema `.sfe` project that contains at least one plugin node type that can be made unavailable for a reload test.
- Action: open the current-schema project with that plugin unavailable, then save it to a new `.sfe` file and reopen the saved copy while the plugin is still unavailable. Expected result: the project opens without schema migration prompts, resolved nodes and edges behave normally, and the save/reopen cycle does not discard the missing-plugin content.
- Action: restore the missing plugin and reopen the saved copy. Expected result: the previously missing node and edge content reappears with its authored properties, styles, and parent relationships intact.
- Action: repeat the save/reopen check with a project that includes nested nodes whose parent shell is temporarily unavailable. Expected result: child nodes load without invalid live parent links while the authored parent relationship is restored once the missing shell plugin is available again.

## Residual Risks

- Pre-current-schema `.sfe` documents are now intentionally rejected; any remaining older files need an out-of-band conversion path before they can be loaded on this branch.
- The live graph model still exposes compatibility properties for overlay state because broader runtime/history/normalization callers are outside this packet's write scope; only the storage ownership moved in P08.

## Ready for Integration

- Yes: current-schema persistence now owns unresolved payload overlays, the packet-owned legacy migration branches are removed, and both required pytest gates passed.
