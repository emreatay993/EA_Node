---
category: math
plugin: core
license: None
---

# math:multiply matrices

**Version: 0.0.0**

## Description

Multiply two matrices using dgemm() for real and zgeem for complex. 

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector_of_double_A_real |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | Real part of the matrix A. |
| <strong>Pin 1</strong>|  vector_of_double_A_imag |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | Imaginary part of the matrix A. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector_of_int_size_A |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | Size of the matrix A. |
| <strong>Pin 3</strong>|  apply_transpose_A |[`bool`](../../core-concepts/dpf-types.md#standard-types) | If this pin is set to true, the transpose to A is applied. Default is false. |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector_of_double_B_real |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | Real part of the matrix B. |
| <strong>Pin 5</strong>|  vector_of_double_B_imag |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | Imaginary part of the matrix B. |
| <strong>Pin 6</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector_of_int_size_B |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | Size of the matrix B. |
| <strong>Pin 7</strong>|  apply_transpose_B |[`bool`](../../core-concepts/dpf-types.md#standard-types) | If this pin is set to true, the transpose to B is applied. Default is false. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| real_results |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | for all cases |
|  **Pin 1**| img_results |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | if expected C=A*B to be complex |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: math

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cgemm

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cgemm"); // operator instantiation
op.connect(0, my_vector_of_double_A_real);
op.connect(1, my_vector_of_double_A_imag);
op.connect(2, my_vector_of_int_size_A);
op.connect(3, my_apply_transpose_A);
op.connect(4, my_vector_of_double_B_real);
op.connect(5, my_vector_of_double_B_imag);
op.connect(6, my_vector_of_int_size_B);
op.connect(7, my_apply_transpose_B);
std::vector<double> my_real_results = op.getOutput<std::vector<double>>(0);
std::vector<double> my_img_results = op.getOutput<std::vector<double>>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.math.None() # operator instantiation
op.inputs.vector_of_double_A_real.connect(my_vector_of_double_A_real)
op.inputs.vector_of_double_A_imag.connect(my_vector_of_double_A_imag)
op.inputs.vector_of_int_size_A.connect(my_vector_of_int_size_A)
op.inputs.apply_transpose_A.connect(my_apply_transpose_A)
op.inputs.vector_of_double_B_real.connect(my_vector_of_double_B_real)
op.inputs.vector_of_double_B_imag.connect(my_vector_of_double_B_imag)
op.inputs.vector_of_int_size_B.connect(my_vector_of_int_size_B)
op.inputs.apply_transpose_B.connect(my_apply_transpose_B)
my_real_results = op.outputs.real_results()
my_img_results = op.outputs.img_results()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.math.None() # operator instantiation
op.inputs.vector_of_double_A_real.Connect(my_vector_of_double_A_real)
op.inputs.vector_of_double_A_imag.Connect(my_vector_of_double_A_imag)
op.inputs.vector_of_int_size_A.Connect(my_vector_of_int_size_A)
op.inputs.apply_transpose_A.Connect(my_apply_transpose_A)
op.inputs.vector_of_double_B_real.Connect(my_vector_of_double_B_real)
op.inputs.vector_of_double_B_imag.Connect(my_vector_of_double_B_imag)
op.inputs.vector_of_int_size_B.Connect(my_vector_of_int_size_B)
op.inputs.apply_transpose_B.Connect(my_apply_transpose_B)
my_real_results = op.outputs.real_results.GetData()
my_img_results = op.outputs.img_results.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.