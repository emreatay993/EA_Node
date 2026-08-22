---
category: None
plugin: math
license: None
---

# lapack::gqr

**Version: 0.0.0**

## Description

Generates the real orthogonal matrix (dorgqr) for real inputs or the complex orthonormal (zungqr) matrix Q of the QR factorization formed by the geqrf  

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  A |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix A. Modified inplace, will store Q values. |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  tau |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Scalar vector tau. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| Q |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Q matrix |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: math

 **Scripting name**: None

 **Full name**: None

 **Internal name**: lapack::gqr

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lapack::gqr"); // operator instantiation
op.connect(0, my_A);
op.connect(1, my_tau);
ansys::dpf::CustomTypeField my_Q = op.getOutput<ansys::dpf::CustomTypeField>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.connect(my_A)
op.inputs.tau.connect(my_tau)
my_Q = op.outputs.Q()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.A.Connect(my_A)
op.inputs.tau.Connect(my_tau)
my_Q = op.outputs.Q.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.