---
category: utility
plugin: N/A
license: any_dpf_supported_increments
---

# utility:multiply fields container 

**Version: 0.0.0**

## Description

Multiply two fields containers or two custom type fields containers using MKL BLAS routines dgemm() for real, and zgemm() for complex: fcC = fcA*fcB. Each field represents a column of fcA/fcB matrices: field data size gives the number of rows and column label scoping size gives the number of columns. The matrix multiplication is performed for each extra label (except complex label which is treated as real/imaginary part of the column). If one label is missing in fcA/fcB, the matrix is considered constant throughout this label.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  container_A |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container or custom types fields container (fcA) representing the left matrix of the multiplication. |
| <strong>Pin 1</strong>|  column_label_A |[`string`](../../core-concepts/dpf-types.md#standard-types) | Label to use as combined columns from the container A (combined column fields must have the same scoping). Default is none. |
| <strong>Pin 2</strong>|  apply_transpose_A |[`bool`](../../core-concepts/dpf-types.md#standard-types) | If this pin is set to true, the transpose of A is applied. Default is false. |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  container_B |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container or custom types fields container (fcB) representing the right matrix of the multiplication. |
| <strong>Pin 4</strong>|  column_label_B |[`string`](../../core-concepts/dpf-types.md#standard-types) | Label to use as combined columns from the container B (combined column fields must have the same scoping). Default is none. |
| <strong>Pin 5</strong>|  apply_transpose_B |[`bool`](../../core-concepts/dpf-types.md#standard-types) | If this pin is set to true, the transpose of B is applied. Default is false. |
| <strong>Pin 6</strong>|  container_incremental |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Incremental fields container or custom type fields container that will be added to the fcA*fcB product. If a non empty fields container is introduced, it will be modified inplace (and sent to the output) to add the contribution of the requested expansion. It is required that the label spaces produced from the multiplication are the same as the incremental ones. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| output |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: N/A

 **Scripting name**: multiply_fields_containers

 **Full name**: utility.multiply_fields_containers

 **Internal name**: multiply_fields_containers

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("multiply_fields_containers"); // operator instantiation
op.connect(0, my_container_A);
op.connect(1, my_column_label_A);
op.connect(2, my_apply_transpose_A);
op.connect(3, my_container_B);
op.connect(4, my_column_label_B);
op.connect(5, my_apply_transpose_B);
op.connect(6, my_container_incremental);
ansys::dpf::FieldsContainer my_output = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.multiply_fields_containers() # operator instantiation
op.inputs.container_A.connect(my_container_A)
op.inputs.column_label_A.connect(my_column_label_A)
op.inputs.apply_transpose_A.connect(my_apply_transpose_A)
op.inputs.container_B.connect(my_container_B)
op.inputs.column_label_B.connect(my_column_label_B)
op.inputs.apply_transpose_B.connect(my_apply_transpose_B)
op.inputs.container_incremental.connect(my_container_incremental)
my_output = op.outputs.output()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.multiply_fields_containers() # operator instantiation
op.inputs.container_A.Connect(my_container_A)
op.inputs.column_label_A.Connect(my_column_label_A)
op.inputs.apply_transpose_A.Connect(my_apply_transpose_A)
op.inputs.container_B.Connect(my_container_B)
op.inputs.column_label_B.Connect(my_column_label_B)
op.inputs.apply_transpose_B.Connect(my_apply_transpose_B)
op.inputs.container_incremental.Connect(my_container_incremental)
my_output = op.outputs.output.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.