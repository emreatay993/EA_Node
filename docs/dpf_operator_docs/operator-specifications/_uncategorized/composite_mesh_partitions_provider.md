---
category: None
plugin: core
license: None
---

# composite::mesh_partitions_provider

**Version: 0.0.0**

## Description

Convert a given scoping into a composite scoping based on a given streams

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  scopings_container |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| scopings_container |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |
|  **Pin 1**| vector<bool> |[`vector<bool>`](../../core-concepts/dpf-types.md#standard-types) |  |
|  **Pin 2**| vector<int32> |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: composite::mesh_partitions_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("composite::mesh_partitions_provider"); // operator instantiation
op.connect(1, my_scopings_container);
op.connect(3, my_streams_container);
ansys::dpf::ScopingsContainer my_scopings_container = op.getOutput<ansys::dpf::ScopingsContainer>(0);
std::vector<bool> my_vector<bool> = op.getOutput<std::vector<bool>>(1);
std::vector<int> my_vector<int32> = op.getOutput<std::vector<int>>(2);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.scopings_container.connect(my_scopings_container)
op.inputs.streams_container.connect(my_streams_container)
my_scopings_container = op.outputs.scopings_container()
my_vector<bool> = op.outputs.vector<bool>()
my_vector<int32> = op.outputs.vector<int32>()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.scopings_container.Connect(my_scopings_container)
op.inputs.streams_container.Connect(my_streams_container)
my_scopings_container = op.outputs.scopings_container.GetData()
my_vector<bool> = op.outputs.vector<bool>.GetData()
my_vector<int32> = op.outputs.vector<int32>.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.