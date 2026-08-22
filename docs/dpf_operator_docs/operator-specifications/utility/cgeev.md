---
category: utility
plugin: core
license: None
---

# utility:eigenvalues and eigenvectors calculator

**Version: 0.0.0**

## Description

Extracts eigenvalues from a real square matrix stored in a vector of doubles. Data must be stored by rows. Uses dgeev for real data.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector_of_double |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | Square matrix with data stored by rows that will be used to calculate the eigenvalues |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| eigenvalues_real_vector |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | eigenvalues real vector |
|  **Pin 1**| eigenvalues_imag_vector |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | eigenvalues imag vector |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cgeev

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cgeev"); // operator instantiation
op.connect(0, my_vector_of_double);
std::vector<double> my_eigenvalues_real_vector = op.getOutput<std::vector<double>>(0);
std::vector<double> my_eigenvalues_imag_vector = op.getOutput<std::vector<double>>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.vector_of_double.connect(my_vector_of_double)
my_eigenvalues_real_vector = op.outputs.eigenvalues_real_vector()
my_eigenvalues_imag_vector = op.outputs.eigenvalues_imag_vector()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.vector_of_double.Connect(my_vector_of_double)
my_eigenvalues_real_vector = op.outputs.eigenvalues_real_vector.GetData()
my_eigenvalues_imag_vector = op.outputs.eigenvalues_imag_vector.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.