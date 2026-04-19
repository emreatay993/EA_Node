---
category: None
plugin: core
license: None
---

# composite::materials_provider

**Version: 0.0.0**

## Description

Creates aggregated data based on a composites streams (distributed over domains)

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| merged_output |[`any`](../../core-concepts/dpf-types.md#any) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **permissive** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, warning checks (like unit or data sizes) won't be done. |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: composite::materials_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("composite::materials_provider"); // operator instantiation
op.connect(3, my_streams_container);
ansys::dpf::Any my_merged_output = op.getOutput<ansys::dpf::Any>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
my_merged_output = op.outputs.merged_output()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.streams_container.Connect(my_streams_container)
my_merged_output = op.outputs.merged_output.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.