---
category: utility
plugin: core
license: None
---

# utility:hierarchical workflow constructor

**Version: 0.0.0**

## Description

Construct a workflow from its interfaces.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| output |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: hierarchical_workflow_constructor

 **Full name**: utility.hierarchical_workflow_constructor

 **Internal name**: workflow::construct_from_interface_hierarchy

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::construct_from_interface_hierarchy"); // operator instantiation
op.connect(0, my_workflow);
ansys::dpf::Workflow my_output = op.getOutput<ansys::dpf::Workflow>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.hierarchical_workflow_constructor() # operator instantiation
op.inputs.workflow.connect(my_workflow)
my_output = op.outputs.output()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.hierarchical_workflow_constructor() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
my_output = op.outputs.output.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.