---
category: metadata
plugin: core
license: None
---

# metadata:remote operator connect

**Version: 0.0.0**

## Description

Creates a CRemoteOperator instance of the input CRemoteOperator or COperator (on 3) on the remote where the Operator (on 0) is located and call "connect" from this remote for a given protocol registered in the streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  left_remote_operator |[`remote_operator`](../../core-concepts/dpf-types.md#remote-operator), [`operator`](../../core-concepts/dpf-types.md#operator) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  input_pin |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  output_pin |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  right_remote_operator |[`remote_operator`](../../core-concepts/dpf-types.md#remote-operator) |  |

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

 **Scripting name**: remote_operator_connect

 **Full name**: metadata.remote_operator_connect

 **Internal name**: remote_operator_connect

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("remote_operator_connect"); // operator instantiation
op.connect(0, my_left_remote_operator);
op.connect(1, my_input_pin);
op.connect(2, my_output_pin);
op.connect(3, my_right_remote_operator);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.remote_operator_connect() # operator instantiation
op.inputs.left_remote_operator.connect(my_left_remote_operator)
op.inputs.input_pin.connect(my_input_pin)
op.inputs.output_pin.connect(my_output_pin)
op.inputs.right_remote_operator.connect(my_right_remote_operator)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.remote_operator_connect() # operator instantiation
op.inputs.left_remote_operator.Connect(my_left_remote_operator)
op.inputs.input_pin.Connect(my_input_pin)
op.inputs.output_pin.Connect(my_output_pin)
op.inputs.right_remote_operator.Connect(my_right_remote_operator)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.