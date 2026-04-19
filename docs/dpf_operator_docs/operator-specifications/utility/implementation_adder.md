---
category: utility
plugin: core
license: None
---

# utility:implementation adder

**Version: 0.0.0**

## Description

Add a implementation for a given interface.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  interface_name |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  implementation |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |

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

 **Scripting name**: implementation_adder

 **Full name**: utility.implementation_adder

 **Internal name**: workflow::add_implementation

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::add_implementation"); // operator instantiation
op.connect(0, my_workflow);
op.connect(1, my_interface_name);
op.connect(2, my_implementation);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.implementation_adder() # operator instantiation
op.inputs.workflow.connect(my_workflow)
op.inputs.interface_name.connect(my_interface_name)
op.inputs.implementation.connect(my_implementation)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.implementation_adder() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
op.inputs.interface_name.Connect(my_interface_name)
op.inputs.implementation.Connect(my_implementation)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.