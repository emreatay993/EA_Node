---
category: math
plugin: core
license: any_dpf_supported_increments
---

# math:mode_contribution

**Version: 0.0.0**

## Description

Compute the mode contribution

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mode_solution |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | mode solution |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mode_shapes |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |
| <strong>Pin 2</strong>|  multi_node_type |[`int32`](../../core-concepts/dpf-types.md#standard-types) | result type for multiple nodes: 0 is minimum, 1 is maximum, 2 is average (default is 2). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| output_component |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: math

 **Plugin**: core

 **Scripting name**: mode_contribution

 **Full name**: math.mode_contribution

 **Internal name**: mode_contribution

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mode_contribution"); // operator instantiation
op.connect(0, my_mode_solution);
op.connect(1, my_mode_shapes);
op.connect(2, my_multi_node_type);
ansys::dpf::FieldsContainer my_output_component = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.math.mode_contribution() # operator instantiation
op.inputs.mode_solution.connect(my_mode_solution)
op.inputs.mode_shapes.connect(my_mode_shapes)
op.inputs.multi_node_type.connect(my_multi_node_type)
my_output_component = op.outputs.output_component()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.math.mode_contribution() # operator instantiation
op.inputs.mode_solution.Connect(my_mode_solution)
op.inputs.mode_shapes.Connect(my_mode_shapes)
op.inputs.multi_node_type.Connect(my_multi_node_type)
my_output_component = op.outputs.output_component.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.