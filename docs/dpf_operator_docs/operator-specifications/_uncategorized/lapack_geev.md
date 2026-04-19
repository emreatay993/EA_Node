---
category: None
plugin: math
license: None
---

# lapack::geev

**Version: 0.0.0**

## Description

Computes the eigenvalues and, optionally, the left and/or right eigenvectors for GE matrices

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  A |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix A. |
| <strong>Pin 1</strong>|  jobvl |[`string`](../../core-concepts/dpf-types.md#standard-types) | computing left eigenvectors of A ('V') or not computing them ('N') (default: 'N'). |
| <strong>Pin 2</strong>|  jobvr |[`string`](../../core-concepts/dpf-types.md#standard-types) | computing right eigenvectors of A ('V') or not computing them ('N') (default: 'N'). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| WR |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | computed eigenvalues (real part in case of dgeev) |
|  **Pin 1**| WI |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | computed eigenvalues (imaginary part in case of dgeev) |
|  **Pin 2**| VL |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | If jobvl = 'V', left eigenvectors |
|  **Pin 3**| VR |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | If jobvr = 'V', right eigenvectors |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: math

 **Scripting name**: None

 **Full name**: None

 **Internal name**: lapack::geev

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lapack::geev"); // operator instantiation
op.connect(0, my_A);
op.connect(1, my_jobvl);
op.connect(2, my_jobvr);
ansys::dpf::CustomTypeField my_WR = op.getOutput<ansys::dpf::CustomTypeField>(0);
ansys::dpf::CustomTypeField my_WI = op.getOutput<ansys::dpf::CustomTypeField>(1);
ansys::dpf::CustomTypeField my_VL = op.getOutput<ansys::dpf::CustomTypeField>(2);
ansys::dpf::CustomTypeField my_VR = op.getOutput<ansys::dpf::CustomTypeField>(3);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.connect(my_A)
op.inputs.jobvl.connect(my_jobvl)
op.inputs.jobvr.connect(my_jobvr)
my_WR = op.outputs.WR()
my_WI = op.outputs.WI()
my_VL = op.outputs.VL()
my_VR = op.outputs.VR()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.Connect(my_A)
op.inputs.jobvl.Connect(my_jobvl)
op.inputs.jobvr.Connect(my_jobvr)
my_WR = op.outputs.WR.GetData()
my_WI = op.outputs.WI.GetData()
my_VL = op.outputs.VL.GetData()
my_VR = op.outputs.VR.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.