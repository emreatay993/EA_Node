---
category: utility
plugin: core
license: None
---

# utility:scale vector

**Version: 0.0.0**

## Description

Scales a vector by a constant

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector_of_double |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | vector with data to be scaled |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  scalar_double |[`double`](../../core-concepts/dpf-types.md#standard-types) | scale factor |
| <strong>Pin 2</strong>|  begin_indx |[`int32`](../../core-concepts/dpf-types.md#standard-types) | starting index (default: 0) |
| <strong>Pin 3</strong>|  elements_spacing |[`int32`](../../core-concepts/dpf-types.md#standard-types) | storage spacing between elements of data (default: 1). The elements between this spacing are kept with the same value as the input |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| vector_of_double |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | scaled vector |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: scale_vector

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("scale_vector"); // operator instantiation
op.connect(0, my_vector_of_double);
op.connect(1, my_scalar_double);
op.connect(2, my_begin_indx);
op.connect(3, my_elements_spacing);
std::vector<double> my_vector_of_double = op.getOutput<std::vector<double>>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.vector_of_double.connect(my_vector_of_double)
op.inputs.scalar_double.connect(my_scalar_double)
op.inputs.begin_indx.connect(my_begin_indx)
op.inputs.elements_spacing.connect(my_elements_spacing)
my_vector_of_double = op.outputs.vector_of_double()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.vector_of_double.Connect(my_vector_of_double)
op.inputs.scalar_double.Connect(my_scalar_double)
op.inputs.begin_indx.Connect(my_begin_indx)
op.inputs.elements_spacing.Connect(my_elements_spacing)
my_vector_of_double = op.outputs.vector_of_double.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.