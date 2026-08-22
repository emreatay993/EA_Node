---
category: metadata
plugin: core
license: None
---

# metadata:remote operator has output pin

**Version: 0.0.0**

## Description

Returns if a remote operator has an output pin after evaluation for a given protocol registered in the streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_op_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  pin |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| has |[`bool`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: remote_operator_has_output_pin

 **Full name**: metadata.remote_operator_has_output_pin

 **Internal name**: remote_operator_has_output_pin

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("remote_operator_has_output_pin"); // operator instantiation
op.connect(0, my_remote_op_id);
op.connect(1, my_pin);
op.connect(3, my_streams_container);
bool my_has = op.getOutput<bool>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.remote_operator_has_output_pin() # operator instantiation
op.inputs.remote_op_id.connect(my_remote_op_id)
op.inputs.pin.connect(my_pin)
op.inputs.streams_container.connect(my_streams_container)
my_has = op.outputs.has()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.remote_operator_has_output_pin() # operator instantiation
op.inputs.remote_op_id.Connect(my_remote_op_id)
op.inputs.pin.Connect(my_pin)
op.inputs.streams_container.Connect(my_streams_container)
my_has = op.outputs.has.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.