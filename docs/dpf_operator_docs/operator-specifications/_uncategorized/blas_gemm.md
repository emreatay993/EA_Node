---
category: None
plugin: math
license: None
---

# blas::gemm

**Version: 0.0.0**

## Description

Multiply two matrices using Lapack functions: dgemm() for real and zgemm() for complex. C = alpha * op(A) * op(B) + beta * C

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  A |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix A |
| <strong>Pin 1</strong>|  apply_transpose_A |[`bool`](../../core-concepts/dpf-types.md#standard-types) | If this pin is set to true, the transpose to A is applied. Default is false. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  B |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix B. |
| <strong>Pin 3</strong>|  apply_transpose_B |[`bool`](../../core-concepts/dpf-types.md#standard-types) | If this pin is set to true, the transpose to B is applied. Default is false. |
| <strong>Pin 4</strong>|  alpha |[`double`](../../core-concepts/dpf-types.md#standard-types) | Default is 1.0. |
| <strong>Pin 5</strong>|  C |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix C. When provided it will be modified in-place with the result of the multiplication and its support will not change. When not provided it will be allocated internally. |
| <strong>Pin 6</strong>|  beta |[`double`](../../core-concepts/dpf-types.md#standard-types) | Default is 0.0. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| C |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Result of the multiplication, double or complex depending on the input. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: math

 **Scripting name**: None

 **Full name**: None

 **Internal name**: blas::gemm

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("blas::gemm"); // operator instantiation
op.connect(0, my_A);
op.connect(1, my_apply_transpose_A);
op.connect(2, my_B);
op.connect(3, my_apply_transpose_B);
op.connect(4, my_alpha);
op.connect(5, my_C);
op.connect(6, my_beta);
ansys::dpf::CustomTypeField my_C = op.getOutput<ansys::dpf::CustomTypeField>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.connect(my_A)
op.inputs.apply_transpose_A.connect(my_apply_transpose_A)
op.inputs.B.connect(my_B)
op.inputs.apply_transpose_B.connect(my_apply_transpose_B)
op.inputs.alpha.connect(my_alpha)
op.inputs.C.connect(my_C)
op.inputs.beta.connect(my_beta)
my_C = op.outputs.C()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.Connect(my_A)
op.inputs.apply_transpose_A.Connect(my_apply_transpose_A)
op.inputs.B.Connect(my_B)
op.inputs.apply_transpose_B.Connect(my_apply_transpose_B)
op.inputs.alpha.Connect(my_alpha)
op.inputs.C.Connect(my_C)
op.inputs.beta.Connect(my_beta)
my_C = op.outputs.C.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.