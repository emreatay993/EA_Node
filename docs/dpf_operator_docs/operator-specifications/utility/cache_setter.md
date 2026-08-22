---
category: utility
plugin: core
license: None
---

# utility:cache setter

**Version: 0.0.0**

## Description

Set and/or update a posteriori caching information inside a workflow.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  output_pin_name |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  level |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  destination |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: cache_setter

 **Full name**: utility.cache_setter

 **Internal name**: workflow::cache_setter

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::cache_setter"); // operator instantiation
op.connect(0, my_workflow);
op.connect(1, my_output_pin_name);
op.connect(2, my_level);
op.connect(3, my_destination);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.cache_setter() # operator instantiation
op.inputs.workflow.connect(my_workflow)
op.inputs.output_pin_name.connect(my_output_pin_name)
op.inputs.level.connect(my_level)
op.inputs.destination.connect(my_destination)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.cache_setter() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
op.inputs.output_pin_name.Connect(my_output_pin_name)
op.inputs.level.Connect(my_level)
op.inputs.destination.Connect(my_destination)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.