---
category: metadata
plugin: core
license: None
---

# metadata:remote workflow erase expose pin

**Version: 0.0.0**

## Description

Erase an exposed input or output pin for a remote workflow for a given protocol registered in the streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin -1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  is_input |[`bool`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  pin_name |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_operator |[`remote_operator`](../../core-concepts/dpf-types.md#remote-operator) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: remote_workflow_erase_pin

 **Full name**: metadata.remote_workflow_erase_pin

 **Internal name**: remote_workflow_erase_pin

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("remote_workflow_erase_pin"); // operator instantiation
op.connect(-1, my_is_input);
op.connect(0, my_pin_name);
op.connect(3, my_remote_operator);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.remote_workflow_erase_pin() # operator instantiation
op.inputs.is_input.connect(my_is_input)
op.inputs.pin_name.connect(my_pin_name)
op.inputs.remote_operator.connect(my_remote_operator)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.remote_workflow_erase_pin() # operator instantiation
op.inputs.is_input.Connect(my_is_input)
op.inputs.pin_name.Connect(my_pin_name)
op.inputs.remote_operator.Connect(my_remote_operator)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.