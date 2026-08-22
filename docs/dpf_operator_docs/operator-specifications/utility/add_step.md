---
category: utility
plugin: core
license: None
---

# utility:add step

**Version: 0.0.0**

## Description

Add step to a workflow.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  step_as_gdc |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  step_name |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |

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

 **Scripting name**: add_step

 **Full name**: utility.add_step

 **Internal name**: workflow::add_step

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::add_step"); // operator instantiation
op.connect(0, my_workflow);
op.connect(1, my_step_as_gdc);
op.connect(2, my_step_name);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.add_step() # operator instantiation
op.inputs.workflow.connect(my_workflow)
op.inputs.step_as_gdc.connect(my_step_as_gdc)
op.inputs.step_name.connect(my_step_name)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.add_step() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
op.inputs.step_as_gdc.Connect(my_step_as_gdc)
op.inputs.step_name.Connect(my_step_name)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.