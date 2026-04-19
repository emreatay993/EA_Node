---
category: math
plugin: core
license: any_dpf_supported_increments
---

# math:qr factorization

**Version: 0.0.0**

## Description

Performs a QR factorization on the input matrix and returns Q & R matrices. Input matrix is column-major.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Matrix with data (column major) |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| Q_matrix |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) |  |
|  **Pin 1**| R_matrix |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: math

 **Plugin**: core

 **Scripting name**: qr_factorization

 **Full name**: math.qr_factorization

 **Internal name**: qr_factorization

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("qr_factorization"); // operator instantiation
op.connect(0, my_field);
ansys::dpf::CustomTypeField my_Q_matrix = op.getOutput<ansys::dpf::CustomTypeField>(0);
ansys::dpf::CustomTypeField my_R_matrix = op.getOutput<ansys::dpf::CustomTypeField>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.math.qr_factorization() # operator instantiation
op.inputs.field.connect(my_field)
my_Q_matrix = op.outputs.Q_matrix()
my_R_matrix = op.outputs.R_matrix()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.math.qr_factorization() # operator instantiation
op.inputs.field.Connect(my_field)
my_Q_matrix = op.outputs.Q_matrix.GetData()
my_R_matrix = op.outputs.R_matrix.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.