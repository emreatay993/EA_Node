---
category: utility
plugin: core
license: None
---

# utility:scale fields container

**Version: 0.0.0**

## Description

Scales a fields container by a constant factor. This factor a fields container, where each value of the vector represents a scaler per component. Number of the components are corresponding to the input field dimensionality

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_containerA |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | fields container to be scaled |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_containerB |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | scaling fields container |
| <strong>Pin 2</strong>|  boolean |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Default is false. If set to true, output of scale is made dimensionless |
| <strong>Pin 3</strong>|  algorithm |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Default is 0 use mkl. If set to 1, don't |
| <strong>Pin 4</strong>|  interpolation_type |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 1:ramped' or 2:stepped', default is ramped |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mechanical::scale_fc

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical::scale_fc"); // operator instantiation
op.connect(0, my_fields_containerA);
op.connect(1, my_fields_containerB);
op.connect(2, my_boolean);
op.connect(3, my_algorithm);
op.connect(4, my_interpolation_type);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.fields_containerA.connect(my_fields_containerA)
op.inputs.fields_containerB.connect(my_fields_containerB)
op.inputs.boolean.connect(my_boolean)
op.inputs.algorithm.connect(my_algorithm)
op.inputs.interpolation_type.connect(my_interpolation_type)
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.fields_containerA.Connect(my_fields_containerA)
op.inputs.fields_containerB.Connect(my_fields_containerB)
op.inputs.boolean.Connect(my_boolean)
op.inputs.algorithm.Connect(my_algorithm)
op.inputs.interpolation_type.Connect(my_interpolation_type)
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.