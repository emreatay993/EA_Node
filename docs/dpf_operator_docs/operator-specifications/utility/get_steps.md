---
category: utility
plugin: core
license: None
---

# utility:get steps

**Version: 0.0.0**

## Description

Get steps to a workflow.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| steps |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: get_steps

 **Full name**: utility.get_steps

 **Internal name**: workflow::get_steps

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::get_steps"); // operator instantiation
op.connect(0, my_workflow);
ansys::dpf::AbstractDataTree my_steps = op.getOutput<ansys::dpf::AbstractDataTree>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.get_steps() # operator instantiation
op.inputs.workflow.connect(my_workflow)
my_steps = op.outputs.steps()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.get_steps() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
my_steps = op.outputs.steps.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.