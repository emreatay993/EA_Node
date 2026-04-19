---
category: utility
plugin: core
license: None
---

# utility:add hierarchy

**Version: 0.0.0**

## Description

Add a hierarchy between two interfaces.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  parent |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  child |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) |  |

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

 **Scripting name**: add_hierarchy

 **Full name**: utility.add_hierarchy

 **Internal name**: workflow::add_interface_hierarchy

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::add_interface_hierarchy"); // operator instantiation
op.connect(0, my_workflow);
op.connect(1, my_parent);
op.connect(2, my_child);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.add_hierarchy() # operator instantiation
op.inputs.workflow.connect(my_workflow)
op.inputs.parent.connect(my_parent)
op.inputs.child.connect(my_child)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.add_hierarchy() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
op.inputs.parent.Connect(my_parent)
op.inputs.child.Connect(my_child)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.