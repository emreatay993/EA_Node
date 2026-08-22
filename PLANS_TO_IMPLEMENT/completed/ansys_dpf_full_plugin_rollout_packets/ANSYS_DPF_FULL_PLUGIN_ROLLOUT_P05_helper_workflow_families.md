# ANSYS_DPF_FULL_PLUGIN_ROLLOUT P05: Helper Workflow Families

## Objective

- Generate the curated DPF helper nodes required for end-to-end visual workflows and place them under role-based library categories that complement the operator catalog.

## Preconditions

- `P03` is marked `PASS` in [ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md](./ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md).
- `P04` may run in parallel, but this packet must not edit operator-owned files.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/nodes/builtins/ansys_dpf_helper_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_helper_adapters.py`
- `tests/test_dpf_generated_helper_catalog.py`
- `tests/test_dpf_workflow_helpers.py`

## Conservative Write Scope

- `ea_node_editor/nodes/builtins/ansys_dpf_helper_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_helper_adapters.py`
- `tests/test_dpf_generated_helper_catalog.py`
- `tests/test_dpf_workflow_helpers.py`
- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P05_helper_workflow_families_WRAPUP.md`

## Required Behavior

- Generate or curate helper nodes for:
  - `DataSources`
  - `StreamsContainer`
  - `Model`
  - `Workflow`
  - `field_from_array`
  - `fields_factory`
  - `fields_container_factory`
  - `mesh_scoping_factory`
  - `time_freq_scoping_factory`
- Generate stable helper node IDs as `dpf.helper.<module>.<callable>`.
- Place helpers under role-based categories such as `Models`, `Scoping`, `Factories`, `Containers`, and `Support`.
- Keep helper wrapping explicit and usable for end-to-end canvas flows rather than reflecting every public instance method.
- Publish the callable binding metadata needed for later runtime materialization.

## Non-Goals

- No operator catalog rollout; that belongs to `P04`.
- No runtime, serializer, or missing-plugin portability work; that belongs to `P06`.
- No broad raw API mirror or literal module dump under `Advanced`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_generated_helper_catalog.py tests/test_dpf_workflow_helpers.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_workflow_helpers.py --ignore=venv -q
```

## Expected Artifacts

- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P05_helper_workflow_families_WRAPUP.md`
- `ea_node_editor/nodes/builtins/ansys_dpf_helper_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_helper_adapters.py`
- `tests/test_dpf_generated_helper_catalog.py`
- `tests/test_dpf_workflow_helpers.py`

## Acceptance Criteria

- Curated helper nodes cover the first-wave workflow surfaces named in the rollout plan.
- Helper IDs and category paths remain stable and role-based.
- Helper wrappers stay focused on usable workflow building blocks rather than broad raw reflection.
- Helper catalog regression anchors pass without touching operator-owned files.

## Handoff Notes

- `P06` consumes the helper metadata emitted here and should not reopen helper-family scope unless inherited runtime tests prove a concrete gap.
