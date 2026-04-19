# ADDON_MANAGER_BACKEND_PREPARATION P03: Generic Missing-Add-On Placeholder Projection

## Objective

- Generalize unresolved-node projection so saved nodes from any missing add-on remain visible on the canvas as locked placeholders, while unresolved docs and edges still survive rebind when the add-on becomes available again.

## Preconditions

- `P00` is marked `PASS`.
- `P01` is marked `PASS`.
- No later `ADDON_MANAGER_BACKEND_PREPARATION` packet is in progress.

## Execution Dependencies

- `P00`
- `P01`

## Target Subsystems

- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/serializer/schema_cases.py`
- `tests/test_registry_validation.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_graph_scene_bridge_bind_regression.py`

## Conservative Write Scope

- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/serializer/schema_cases.py`
- `tests/test_registry_validation.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `docs/specs/work_packets/addon_manager_backend_preparation/P03_generic_missing_addon_placeholder_projection_WRAPUP.md`

## Required Behavior

- Replace the special-case DPF placeholder path with a generic unresolved add-on placeholder contract.
- Carry add-on-facing metadata needed by later packets, including add-on identity, unavailable reason, and locked-state payload fields.
- Preserve unresolved node docs and unresolved edge docs in persistence so reopening and later rebind still work.
- Keep non-missing nodes and existing non-add-on workflows unchanged.
- Update inherited serializer and registry validation anchors in place when the placeholder contract changes.

## Non-Goals

- No QML interaction blocking or Mockup B visual chrome yet; that belongs to `P04`.
- No DPF extraction or runtime rebuild yet; those belong to `P05` and `P06`.
- No Add-On Manager UI yet; that belongs to `P07`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_registry_validation.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_registry_validation.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/addon_manager_backend_preparation/P03_generic_missing_addon_placeholder_projection_WRAPUP.md`

## Acceptance Criteria

- Missing add-on nodes remain visible in scene payloads instead of staying persistence-only.
- Rebind behavior for later add-on availability is preserved.
- The placeholder payload carries stable locked-node metadata for later graph and Add-On Manager packets.
- The inherited serializer, migration, and graph-scene regression anchors pass.

## Handoff Notes

- `P04`, `P06`, and `P07` consume this payload. Do not rename placeholder payload fields later unless the inherited regression anchors and downstream packet specs are updated together.
