---
category: math
plugin: core
license: None
---

# math:make transfer function input

**Version: 0.0.0**

## Description

Prepare unitary input data required to build the transfer function matrix.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  physical_input_dofs |[`property_field`](../../core-concepts/dpf-types.md#property-field) | Property field containing the physical input dofs defined by their dof component number and the associated node scoping (property field scoping).Dof component number are mapped as follows with physical dofs: 0=UX, 1=UY, 2=UZ, 3=ROTX, 4=ROTY, 5=ROTZ. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  time_scoping |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`int32`](../../core-concepts/dpf-types.md#standard-types) | Load step number, the input load are computed only on this time scoping. |
| <strong>Pin 3</strong>|  input_type |[`int32`](../../core-concepts/dpf-types.md#standard-types) | If this pin is set to 1, input in time domain is considered. By default input in frequency domain is considered. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | fields container of the input described by the input_dof_index label |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: math

 **Plugin**: core

 **Scripting name**: make_tf_input

 **Full name**: math.make_tf_input

 **Internal name**: make_tf_input

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("make_tf_input"); // operator instantiation
op.connect(0, my_physical_input_dofs);
op.connect(2, my_time_scoping);
op.connect(3, my_input_type);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.math.make_tf_input() # operator instantiation
op.inputs.physical_input_dofs.connect(my_physical_input_dofs)
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.input_type.connect(my_input_type)
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.math.make_tf_input() # operator instantiation
op.inputs.physical_input_dofs.Connect(my_physical_input_dofs)
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.input_type.Connect(my_input_type)
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.