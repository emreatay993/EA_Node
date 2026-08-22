---
category: None
plugin: math
license: None
---

# lapack::sygv

**Version: 0.0.0**

## Description

computes all the eigenvalues, and optionally, the eigenvectors of a real generalized symmetric - definite eigenproblem, of the form A * x = (lambda)*B * x, A * Bx = (lambda)*x, or B * A * x = (lambda)*x. Here A and B are assumed to be symmetric and B is also positive definite.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  A |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix A. |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  B |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix B. |
| <strong>Pin 2</strong>|  jobz |[`string`](../../core-concepts/dpf-types.md#standard-types) | computing eigenvectors of A ('V') or not computing them ('N') (default: 'N'). |
| <strong>Pin 3</strong>|  itype |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Specifies the problem type to be solved: 1:  A*x = (lambda)*B*x , 2:  A*B*x = (lambda)*x, 3:  B*A*x = (lambda)*x. (default: 1). |
| <strong>Pin 4</strong>|  uplo |[`string`](../../core-concepts/dpf-types.md#standard-types) | Upper triangles of A and B are stored ('U') or lower triangles of A and B are stored ('L') (default: 'U'). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| W |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | computed eigenvalues |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: math

 **Scripting name**: None

 **Full name**: None

 **Internal name**: lapack::sygv

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lapack::sygv"); // operator instantiation
op.connect(0, my_A);
op.connect(1, my_B);
op.connect(2, my_jobz);
op.connect(3, my_itype);
op.connect(4, my_uplo);
ansys::dpf::CustomTypeField my_W = op.getOutput<ansys::dpf::CustomTypeField>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.connect(my_A)
op.inputs.B.connect(my_B)
op.inputs.jobz.connect(my_jobz)
op.inputs.itype.connect(my_itype)
op.inputs.uplo.connect(my_uplo)
my_W = op.outputs.W()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.Connect(my_A)
op.inputs.B.Connect(my_B)
op.inputs.jobz.Connect(my_jobz)
op.inputs.itype.Connect(my_itype)
op.inputs.uplo.Connect(my_uplo)
my_W = op.outputs.W.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.