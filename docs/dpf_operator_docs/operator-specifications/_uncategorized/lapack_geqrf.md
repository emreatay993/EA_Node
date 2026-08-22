---
category: None
plugin: math
license: None
---

# lapack::geqrf

**Version: 0.0.0**

## Description

Computes the QR factorization of a general m-by-n matrix

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  A |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix A. Modified inplace, will store R values. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| R |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Overwritten by the factorization data. The elements on and above the diagonal of the array contain the min(m,n) by n upper trapezoidal matrix R (R is upper triangular if m is bigger or equal to n) |
|  **Pin 1**| tau |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Array that contains scalar factor of the elementary reflector H(i) |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: math

 **Scripting name**: None

 **Full name**: None

 **Internal name**: lapack::geqrf

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lapack::geqrf"); // operator instantiation
op.connect(0, my_A);
ansys::dpf::CustomTypeField my_R = op.getOutput<ansys::dpf::CustomTypeField>(0);
ansys::dpf::CustomTypeField my_tau = op.getOutput<ansys::dpf::CustomTypeField>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.connect(my_A)
my_R = op.outputs.R()
my_tau = op.outputs.tau()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.Connect(my_A)
my_R = op.outputs.R.GetData()
my_tau = op.outputs.tau.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.