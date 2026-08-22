---
category: None
plugin: N/A
license: None
---

# identity_matrix

**Version: 0.0.0**

## Description

Generates an identity matrix with the dimensionality and type defined by the inputs

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  matrix_dimensionality |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | vector with matrix dimensions |
| <strong>Pin 1</strong>|  type |[`string`](../../core-concepts/dpf-types.md#standard-types) | Type of the custom type fields_container. Accepted values: double, complex<double>. Default: double |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| matrix |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Field matrix containing the identity matrix. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: identity_matrix

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("identity_matrix"); // operator instantiation
op.connect(0, my_matrix_dimensionality);
op.connect(1, my_type);
ansys::dpf::CustomTypeField my_matrix = op.getOutput<ansys::dpf::CustomTypeField>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.matrix_dimensionality.connect(my_matrix_dimensionality)
op.inputs.type.connect(my_type)
my_matrix = op.outputs.matrix()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.matrix_dimensionality.Connect(my_matrix_dimensionality)
op.inputs.type.Connect(my_type)
my_matrix = op.outputs.matrix.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.