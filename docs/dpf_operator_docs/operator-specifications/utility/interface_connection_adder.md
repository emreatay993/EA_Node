---
category: utility
plugin: core
license: None
---

# utility:interface connection adder

**Version: 0.0.0**

## Description

Add a connection between two intefaces.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  left_dt |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  right_dt |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  left_pin |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  right_pin |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |

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

 **Scripting name**: interface_connection_adder

 **Full name**: utility.interface_connection_adder

 **Internal name**: workflow::add_interface_connection

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::add_interface_connection"); // operator instantiation
op.connect(0, my_workflow);
op.connect(1, my_left_dt);
op.connect(2, my_right_dt);
op.connect(3, my_left_pin);
op.connect(4, my_right_pin);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.interface_connection_adder() # operator instantiation
op.inputs.workflow.connect(my_workflow)
op.inputs.left_dt.connect(my_left_dt)
op.inputs.right_dt.connect(my_right_dt)
op.inputs.left_pin.connect(my_left_pin)
op.inputs.right_pin.connect(my_right_pin)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.interface_connection_adder() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
op.inputs.left_dt.Connect(my_left_dt)
op.inputs.right_dt.Connect(my_right_dt)
op.inputs.left_pin.Connect(my_left_pin)
op.inputs.right_pin.Connect(my_right_pin)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.