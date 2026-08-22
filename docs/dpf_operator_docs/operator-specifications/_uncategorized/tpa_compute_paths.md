---
category: None
plugin: N/A
license: any_dpf_supported_increments
---

# tpa::compute_paths

**Version: 0.0.0**

## Description

Compute transfer paths, output displacements and assembled blocked forces of a system analyzed with Transfer Path Analysis (TPA).

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  B_fc |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container of the connectivity matrix for each TPA component. |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  Y_inter_inter_fc |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container of the FRF matrix giving interface dofs displacements as a function of interface dofs forces for each TPA component. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  Y_inter_input_fc |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container of the FRF matrix giving interface dofs displacements as a function of input dofs forces for each TPA component. |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  Y_output_inter_fc |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container of the FRF matrix giving output dofs displacements as a function of interface dofs forces for each TPA component. |
| <strong>Pin 4</strong>|  Y_output_input_fc |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container of the FRF matrix giving output dofs displacements as a function of input dofs forces for each TPA component. |
| <strong>Pin 5</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  F_input_fc |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container of the external force vector for each TPA component. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| transfer_paths_fc |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container of TPA transfer paths. |
|  **Pin 1**| output_displacement_fc |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container of the total displacement at output dofs. |
|  **Pin 2**| blocked_forces_fc |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container of the interface blocked forces. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: tpa::compute_paths

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("tpa::compute_paths"); // operator instantiation
op.connect(0, my_B_fc);
op.connect(1, my_Y_inter_inter_fc);
op.connect(2, my_Y_inter_input_fc);
op.connect(3, my_Y_output_inter_fc);
op.connect(4, my_Y_output_input_fc);
op.connect(5, my_F_input_fc);
ansys::dpf::FieldsContainer my_transfer_paths_fc = op.getOutput<ansys::dpf::FieldsContainer>(0);
ansys::dpf::FieldsContainer my_output_displacement_fc = op.getOutput<ansys::dpf::FieldsContainer>(1);
ansys::dpf::FieldsContainer my_blocked_forces_fc = op.getOutput<ansys::dpf::FieldsContainer>(2);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.B_fc.connect(my_B_fc)
op.inputs.Y_inter_inter_fc.connect(my_Y_inter_inter_fc)
op.inputs.Y_inter_input_fc.connect(my_Y_inter_input_fc)
op.inputs.Y_output_inter_fc.connect(my_Y_output_inter_fc)
op.inputs.Y_output_input_fc.connect(my_Y_output_input_fc)
op.inputs.F_input_fc.connect(my_F_input_fc)
my_transfer_paths_fc = op.outputs.transfer_paths_fc()
my_output_displacement_fc = op.outputs.output_displacement_fc()
my_blocked_forces_fc = op.outputs.blocked_forces_fc()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.B_fc.Connect(my_B_fc)
op.inputs.Y_inter_inter_fc.Connect(my_Y_inter_inter_fc)
op.inputs.Y_inter_input_fc.Connect(my_Y_inter_input_fc)
op.inputs.Y_output_inter_fc.Connect(my_Y_output_inter_fc)
op.inputs.Y_output_input_fc.Connect(my_Y_output_input_fc)
op.inputs.F_input_fc.Connect(my_F_input_fc)
my_transfer_paths_fc = op.outputs.transfer_paths_fc.GetData()
my_output_displacement_fc = op.outputs.output_displacement_fc.GetData()
my_blocked_forces_fc = op.outputs.blocked_forces_fc.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.