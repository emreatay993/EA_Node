---
category: None
plugin: N/A
license: None
---

# eigenanalysis

**Version: 0.0.0**

## Description

Computes the eigenvalues and eigenvectors (left and right) of a matrix.If left and right eigenvectors are equal, eigenvectors are output in pin(1)A real nonsymmetric matrix can generate complex conjugate eigenvalues and eigenvectors, thus outputs are of complex type.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  matrix |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  compute_eigenvectors |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Boolean that determines if the eigenvectors will be computed. Default = False. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| eigenvalues |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Field matrix containing the eigenvalues ot the input matrix. |
|  **Pin 1**| left_eigenvectors |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Field matrix containing the left eigenvectors ot the input matrix. |
|  **Pin 2**| right_eigenvectors |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Field matrix containing the right eigenvectors ot the input matrix. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: eigenanalysis

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("eigenanalysis"); // operator instantiation
op.connect(0, my_matrix);
op.connect(1, my_compute_eigenvectors);
ansys::dpf::CustomTypeField my_eigenvalues = op.getOutput<ansys::dpf::CustomTypeField>(0);
ansys::dpf::CustomTypeField my_left_eigenvectors = op.getOutput<ansys::dpf::CustomTypeField>(1);
ansys::dpf::CustomTypeField my_right_eigenvectors = op.getOutput<ansys::dpf::CustomTypeField>(2);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.matrix.connect(my_matrix)
op.inputs.compute_eigenvectors.connect(my_compute_eigenvectors)
my_eigenvalues = op.outputs.eigenvalues()
my_left_eigenvectors = op.outputs.left_eigenvectors()
my_right_eigenvectors = op.outputs.right_eigenvectors()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.matrix.Connect(my_matrix)
op.inputs.compute_eigenvectors.Connect(my_compute_eigenvectors)
my_eigenvalues = op.outputs.eigenvalues.GetData()
my_left_eigenvectors = op.outputs.left_eigenvectors.GetData()
my_right_eigenvectors = op.outputs.right_eigenvectors.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.