# ANSYS_DPF_FULL_PLUGIN_ROLLOUT P06: Runtime Persistence Portability

## Objective

- Extend runtime materialization, execution binding, serializer portability, and missing-plugin reopen behavior to the generated operator and helper nodes emitted by earlier packets.

## Preconditions

- `P04` and `P05` are marked `PASS` in [ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md](./ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md).
- No later `ANSYS_DPF_FULL_PLUGIN_ROLLOUT` packet is in progress.

## Execution Dependencies

- `P04`
- `P05`

## Target Subsystems

- `ea_node_editor/execution/dpf_runtime/base.py`
- `ea_node_editor/execution/dpf_runtime/contracts.py`
- `ea_node_editor/execution/dpf_runtime/materialization.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_dpf_materialization.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`

## Conservative Write Scope

- `ea_node_editor/execution/dpf_runtime/base.py`
- `ea_node_editor/execution/dpf_runtime/contracts.py`
- `ea_node_editor/execution/dpf_runtime/materialization.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_dpf_materialization.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P06_runtime_persistence_portability_WRAPUP.md`

## Required Behavior

- Materialize and execute generated operator-backed nodes using the metadata produced by `P04`.
- Materialize and execute generated helper-backed nodes using the metadata produced by `P05`.
- Add handle kinds or generic fallback handle paths for helper objects that do not justify bespoke runtime handle classes.
- Preserve optional-port exposure state, saved properties, labels, and connectivity when reopening generated DPF nodes without DPF installed.
- Keep generated DPF nodes non-executable and read-only when the plugin is unavailable.
- Update inherited serializer and materialization regression anchors in place.

## Non-Goals

- No taxonomy or catalog reorganization beyond what runtime adoption strictly requires.
- No broader UI redesign of the node library.
- No broad raw API mirror rollout.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_materialization.py tests/test_dpf_runtime_service.py tests/test_serializer.py tests/test_serializer_schema_migration.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_materialization.py tests/test_serializer.py --ignore=venv -q
```

## Expected Artifacts

- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P06_runtime_persistence_portability_WRAPUP.md`
- `ea_node_editor/execution/dpf_runtime/base.py`
- `ea_node_editor/execution/dpf_runtime/contracts.py`
- `ea_node_editor/execution/dpf_runtime/materialization.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_dpf_materialization.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`

## Acceptance Criteria

- Generated operator and helper nodes execute through the DPF runtime seam.
- Runtime handle materialization supports the first-wave helper object families plus a generic fallback for the rest.
- Save and reopen preserve generated DPF nodes as read-only placeholders when DPF is missing.
- Runtime and serializer regression anchors pass.

## Handoff Notes

- `P07` publishes the retained evidence from this packet and should not widen runtime adoption semantics unless a closeout regression proves it necessary.
