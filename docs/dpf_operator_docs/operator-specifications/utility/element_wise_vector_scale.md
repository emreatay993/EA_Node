---
category: utility
plugin: core
license: None
---

# utility:element wise vector scale

**Version: 0.0.0**

## Description

Performs element by element multiplication of vector A and vector B.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector_of_double |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | vector with data to be scaled |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector_scales |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | vector with scale factors, assumed the size is the same as the vector to be scaled |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| scaled_vector |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | scaled vector |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: element_wise_vector_scale

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("element_wise_vector_scale"); // operator instantiation
op.connect(0, my_vector_of_double);
op.connect(1, my_vector_scales);
std::vector<double> my_scaled_vector = op.getOutput<std::vector<double>>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.vector_of_double.connect(my_vector_of_double)
op.inputs.vector_scales.connect(my_vector_scales)
my_scaled_vector = op.outputs.scaled_vector()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.vector_of_double.Connect(my_vector_of_double)
op.inputs.vector_scales.Connect(my_vector_scales)
my_scaled_vector = op.outputs.scaled_vector.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.