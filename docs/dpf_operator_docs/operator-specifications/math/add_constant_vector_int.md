---
category: math
plugin: core
license: None
---

# math:add_constant_vector_int

**Version: 0.0.0**

## Description

Computes the sum of a int vector (in 0) and a int scalar (in 1). If an int is provided as a threshold value (in 2), all values of the input vector (in 0) above or equal to it will not be modified.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector_of_int |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | vector of int |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  weights |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | int or vector of int |
| <strong>Pin 2</strong>|  threshold_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Threshold value |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| vector<int32> |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: math

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: add_constant_vector_int

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("add_constant_vector_int"); // operator instantiation
op.connect(0, my_vector_of_int);
op.connect(1, my_weights);
op.connect(2, my_threshold_id);
std::vector<int> my_vector<int32> = op.getOutput<std::vector<int>>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.math.None() # operator instantiation
op.inputs.vector_of_int.connect(my_vector_of_int)
op.inputs.weights.connect(my_weights)
op.inputs.threshold_id.connect(my_threshold_id)
my_vector<int32> = op.outputs.vector<int32>()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.math.None() # operator instantiation
op.inputs.vector_of_int.Connect(my_vector_of_int)
op.inputs.weights.Connect(my_weights)
op.inputs.threshold_id.Connect(my_threshold_id)
my_vector<int32> = op.outputs.vector<int32>.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.