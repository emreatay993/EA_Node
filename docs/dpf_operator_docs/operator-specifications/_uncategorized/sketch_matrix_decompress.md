---
category: None
plugin: N/A
license: None
---

# sketch_matrix_decompress

**Version: 0.0.0**

## Description

Decompress fields container using an orthonormal randomized (Gaussian distribution) sketch matrix.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  dataIn |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container to be decompressed. It is assumed that all fields have the same structure (scoping, num_entities). |
| <strong>Pin 1</strong>|  sketch_matrix |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Field containing the sketch matrix. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| dataOut |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | the output matrix is a 'fields_container';                     each field correspond to the multiplication of the sketch matrix by the original fields. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: sketch_matrix_decompress

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("sketch_matrix_decompress"); // operator instantiation
op.connect(0, my_dataIn);
op.connect(1, my_sketch_matrix);
ansys::dpf::FieldsContainer my_dataOut = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.dataIn.connect(my_dataIn)
op.inputs.sketch_matrix.connect(my_sketch_matrix)
my_dataOut = op.outputs.dataOut()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.dataIn.Connect(my_dataIn)
op.inputs.sketch_matrix.Connect(my_sketch_matrix)
my_dataOut = op.outputs.dataOut.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.