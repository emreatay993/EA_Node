---
category: None
plugin: math
license: None
---

# lapack::gesvd

**Version: 0.0.0**

## Description

GESVD computes the singular value decomposition (SVD) of a double or complex matrix A with size M-by-N. A = U * SIGMA * transpose(V) 

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  A |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix A |
| <strong>Pin 1</strong>|  jobu |[`string`](../../core-concepts/dpf-types.md#standard-types) | computing all [M,M] ('A') or part of the matrix U [M, min(M,N)] ('S') (default: 'S'). |
| <strong>Pin 2</strong>|  jobvt |[`string`](../../core-concepts/dpf-types.md#standard-types) | computing all [N,N] ('A') or part of the matrix V**H [min(M,N), N] ('S') (default: 'S'). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| U |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Left singular vectors of A, M-by-M orthogonal matrix double or complex depending on the input. |
|  **Pin 1**| S |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | The singular values of A in a descending order, vector of double. |
|  **Pin 2**| Vt |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Right singular vectors of A, N-by-N orthogonal matrix, double or complex depending on the input. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: math

 **Scripting name**: None

 **Full name**: None

 **Internal name**: lapack::gesvd

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lapack::gesvd"); // operator instantiation
op.connect(0, my_A);
op.connect(1, my_jobu);
op.connect(2, my_jobvt);
ansys::dpf::CustomTypeField my_U = op.getOutput<ansys::dpf::CustomTypeField>(0);
ansys::dpf::CustomTypeField my_S = op.getOutput<ansys::dpf::CustomTypeField>(1);
ansys::dpf::CustomTypeField my_Vt = op.getOutput<ansys::dpf::CustomTypeField>(2);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.connect(my_A)
op.inputs.jobu.connect(my_jobu)
op.inputs.jobvt.connect(my_jobvt)
my_U = op.outputs.U()
my_S = op.outputs.S()
my_Vt = op.outputs.Vt()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.Connect(my_A)
op.inputs.jobu.Connect(my_jobu)
op.inputs.jobvt.Connect(my_jobvt)
my_U = op.outputs.U.GetData()
my_S = op.outputs.S.GetData()
my_Vt = op.outputs.Vt.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.