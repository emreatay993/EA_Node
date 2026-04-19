# P03 Generic Missing-Add-On Placeholder Projection Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/addon-manager-backend-preparation/p03-generic-missing-addon-placeholder-projection`
- Commit Owner: `worker`
- Commit SHA: `0bd94d2971e04c48c1887bf377c9937e4a5c9569`
- Changed Files: `docs/specs/work_packets/addon_manager_backend_preparation/P03_generic_missing_addon_placeholder_projection_WRAPUP.md`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/persistence/overlay.py`, `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `tests/serializer/schema_cases.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_registry_validation.py`, `tests/test_serializer.py`, `tests/test_serializer_schema_migration.py`
- Artifacts Produced: `docs/specs/work_packets/addon_manager_backend_preparation/P03_generic_missing_addon_placeholder_projection_WRAPUP.md`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/persistence/overlay.py`, `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `tests/serializer/schema_cases.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_registry_validation.py`, `tests/test_serializer.py`, `tests/test_serializer_schema_migration.py`

- Introduced a generic missing-add-on placeholder contract in persistence so unresolved add-on-backed node docs now carry stable add-on identity, apply policy, status, unavailable summary, and locked-state metadata without changing existing non-add-on unresolved payloads.
- Replaced the DPF-only scene projection path with generic placeholder projection driven by that contract, so missing add-on nodes from any registered add-on remain visible on the canvas with their saved titles, properties, hidden-port state, and surviving unresolved edges.
- Updated normalization and codec flows so unresolved add-on docs are enriched consistently on load, save, runtime-envelope capture, and live registry normalization, while preserving later rebind of nodes and edges when descriptors return.
- Refreshed the inherited serializer, migration, registry-validation, and scene-bridge anchors to cover the generic placeholder contract and to keep the packet review gate stable in environments where the local DPF catalog surface is broader than the foundational baseline.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_registry_validation.py --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_registry_validation.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree from `C:\w\ea_node_ed-p03-87c877` with `.\venv\Scripts\python.exe main.py`, and use a project file that contains add-on-backed nodes whose add-on is not loaded in the current session.

1. Missing add-on canvas projection
Action: open a project authored with add-on-backed nodes while the corresponding add-on is unavailable or otherwise not loaded into the current registry.
Expected result: the saved nodes remain visible on the canvas instead of disappearing into persistence-only state, and any surviving unresolved edges between visible nodes still render.

2. Save and reopen round trip
Action: save the project in the missing-add-on session, close it, and reopen the saved file in the same session.
Expected result: the same placeholder nodes and unresolved edges return in the same positions with their saved titles, properties, and hidden-port behavior intact.

3. Rebind smoke
Action: reopen the same project in a session where the add-on is loaded again.
Expected result: the placeholder nodes rebind back to live nodes without losing their saved properties or edge structure; the packet-owned automated tests remain the primary proof for the hidden-edge and migration branches of this flow.

## Residual Risks

- Placeholder projection depends on the `P01` add-on contract; unresolved nodes from plugins that never publish an add-on record still follow the older persistence-only unresolved path.
- The inherited verification commands still emit ambient ANSYS DPF deprecation warnings from the local third-party package, but the packet-owned review gate and full verification command pass.

## Ready for Integration

- Yes: the generic missing-add-on placeholder contract, scene projection, persistence round-trip coverage, and rebind regressions are all landed and the required packet verification commands pass.
