---
category: None
plugin: math
license: None
---

# lapack::gels

**Version: 0.0.0**

## Description

Least squares solving using QR/LQ decomposition: dgels() for real and zgels() for complex.
For over-determined problems, minimize ||A*X-B||.
For under-determined problems, find min(X) such that A*X=B.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  A |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix A representing the set of linear systems. A will be overwritten by QR/LQ factorization. |
| <strong>Pin 1</strong>|  apply_transpose_A |[`bool`](../../core-concepts/dpf-types.md#standard-types) | If this pin is set to true, the transpose to A is applied. Default is false. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  B |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix B representing the right-hand side (several right-hand sides can be handled, they are stored as the columns of B). B will be overwritten by result values. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| B |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Result of A*X=B in least squares sense (the number of columns is the same as the number of columns of B). |
|  **Pin 1**| A |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Details of the QR (for well-determined and over-determined problems) or LQ (for under-determined problems) factorization. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: math

 **Scripting name**: None

 **Full name**: None

 **Internal name**: lapack::gels

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lapack::gels"); // operator instantiation
op.connect(0, my_A);
op.connect(1, my_apply_transpose_A);
op.connect(2, my_B);
ansys::dpf::CustomTypeField my_B = op.getOutput<ansys::dpf::CustomTypeField>(0);
ansys::dpf::CustomTypeField my_A = op.getOutput<ansys::dpf::CustomTypeField>(1);
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
my_B = op.outputs.B()
my_A = op.outputs.A()
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
my_B = op.outputs.B.GetData()
my_A = op.outputs.A.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.