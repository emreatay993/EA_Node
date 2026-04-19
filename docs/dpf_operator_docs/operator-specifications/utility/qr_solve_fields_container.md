---
category: utility
plugin: N/A
license: any_dpf_supported_increments
---

# utility:QR solve fields container

**Version: 0.0.0**

## Description

Solve linear system A*X = B using QR solve algorithm for input fields containers A and B. Each field data represents a column of the matrix.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  matrices_A |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container or custom types fields container for the linear system matrix A. |
| <strong>Pin 1</strong>|  column_label_A |[`string`](../../core-concepts/dpf-types.md#standard-types) | Label defining the columns of the container A. Default is none. |
| <strong>Pin 2</strong>|  apply_transpose_A |[`bool`](../../core-concepts/dpf-types.md#standard-types) | If this pin is set to true, the transpose of A is applied. Default is false. |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  matrices_B |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container or custom types fields container for the linear system matrix B. |
| <strong>Pin 4</strong>|  column_label_B |[`string`](../../core-concepts/dpf-types.md#standard-types) | Label defining the columns of the container B. Default is none. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**|  |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: N/A

 **Scripting name**: qr_solve_fields_container

 **Full name**: utility.qr_solve_fields_container

 **Internal name**: qr_solve_fields_container

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("qr_solve_fields_container"); // operator instantiation
op.connect(0, my_matrices_A);
op.connect(1, my_column_label_A);
op.connect(2, my_apply_transpose_A);
op.connect(3, my_matrices_B);
op.connect(4, my_column_label_B);
ansys::dpf::FieldsContainer my_ = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.qr_solve_fields_container() # operator instantiation
op.inputs.matrices_A.connect(my_matrices_A)
op.inputs.column_label_A.connect(my_column_label_A)
op.inputs.apply_transpose_A.connect(my_apply_transpose_A)
op.inputs.matrices_B.connect(my_matrices_B)
op.inputs.column_label_B.connect(my_column_label_B)
my_ = op.outputs.()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.qr_solve_fields_container() # operator instantiation
op.inputs.matrices_A.Connect(my_matrices_A)
op.inputs.column_label_A.Connect(my_column_label_A)
op.inputs.apply_transpose_A.Connect(my_apply_transpose_A)
op.inputs.matrices_B.Connect(my_matrices_B)
op.inputs.column_label_B.Connect(my_column_label_B)
my_ = op.outputs..GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.