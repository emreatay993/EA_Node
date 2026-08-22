# ANSYS_DPF_FULL_PLUGIN_ROLLOUT P04: Operator Families

## Objective

- Generate the full `dpf.operators.*` catalog under stable family-based node categories using the contracts and taxonomy established by earlier packets.

## Preconditions

- `P03` is marked `PASS` in [ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md](./ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md).
- `P05` may run in parallel, but this packet must not edit helper-owned files.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `tests/test_dpf_generated_operator_catalog.py`
- `tests/test_dpf_node_catalog.py`

## Conservative Write Scope

- `ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `tests/test_dpf_generated_operator_catalog.py`
- `tests/test_dpf_node_catalog.py`
- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P04_operator_families_WRAPUP.md`

## Required Behavior

- Enumerate and expose the full `dpf.operators.*` surface from the installed DPF library.
- Generate stable operator node IDs as `dpf.op.<family>.<name>`.
- Place generated operators under `Ansys DPF > Operators > <family>`.
- Map required pins to exposed ports.
- Map optional object-like pins to hidden optional ports.
- Map optional scalar, enum, string, and bool pins to properties, with optional port exposure only when the type mapping remains coherent.
- Use accepted type sets for mixed-type pins and preserve pin source metadata for execution.
- Update inherited DPF catalog regression anchors in place.

## Non-Goals

- No helper-callable rollout; that belongs to `P05`.
- No runtime, serializer, or missing-plugin work; that belongs to `P06`.
- No broad raw API mirror under `Advanced`; that remains deferred.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_generated_operator_catalog.py tests/test_dpf_node_catalog.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_generated_operator_catalog.py --ignore=venv -q
```

## Expected Artifacts

- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P04_operator_families_WRAPUP.md`
- `ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `tests/test_dpf_generated_operator_catalog.py`
- `tests/test_dpf_node_catalog.py`

## Acceptance Criteria

- The generated operator catalog covers the installed `dpf.operators.*` families.
- Generated operator IDs and category paths remain stable and family-based.
- Optional pins are represented according to the contract rules from `P02`.
- Operator catalog regression anchors pass without touching helper-owned files.

## Handoff Notes

- `P06` consumes the operator metadata emitted here and should only reopen operator-generation semantics if inherited runtime tests prove a gap.
