---
category: None
plugin: core
license: None
---

# RegularizedMaximum

**Version: 0.0.0**

## Description

Aggregate a field (in 0) by computing its average value

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 1</strong>|  weights |[`field`](../../core-concepts/dpf-types.md#field) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| double_or_vector_double |[`double`](../../core-concepts/dpf-types.md#standard-types), [`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | Double or Double vector |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: RegularizedMaximum

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("RegularizedMaximum"); // operator instantiation
op.connect(0, my_field);
op.connect(1, my_weights);
double my_double_or_vector_double = op.getOutput<double>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.field.connect(my_field)
op.inputs.weights.connect(my_weights)
my_double_or_vector_double_as_double = op.outputs.double_or_vector_double_as_double()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.field.Connect(my_field)
op.inputs.weights.Connect(my_weights)
my_double_or_vector_double = op.outputs.double_or_vector_double.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.