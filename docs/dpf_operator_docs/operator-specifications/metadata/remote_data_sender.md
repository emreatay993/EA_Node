---
category: metadata
plugin: core
license: None
---

# metadata:remote data sender

**Version: 0.0.0**

## Description

Sends the local data to a remote for a given protocol registered in the streams and connect it to the remote workflow on the requested pin.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_workflow_input_name |[`string`](../../core-concepts/dpf-types.md#standard-types) | name of the remote workflow input where the local data should be connected |
| <strong>Pin 3</strong>|  remote_workflow |[`remote_workflow`](../../core-concepts/dpf-types.md#remote-workflow) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| local_data |[`any`](../../core-concepts/dpf-types.md#any) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: remote_data_sender

 **Full name**: metadata.remote_data_sender

 **Internal name**: remote_data_sender

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("remote_data_sender"); // operator instantiation
op.connect(1, my_remote_workflow_input_name);
op.connect(3, my_remote_workflow);
ansys::dpf::Any my_local_data = op.getOutput<ansys::dpf::Any>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.remote_data_sender() # operator instantiation
op.inputs.remote_workflow_input_name.connect(my_remote_workflow_input_name)
op.inputs.remote_workflow.connect(my_remote_workflow)
my_local_data = op.outputs.local_data()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.remote_data_sender() # operator instantiation
op.inputs.remote_workflow_input_name.Connect(my_remote_workflow_input_name)
op.inputs.remote_workflow.Connect(my_remote_workflow)
my_local_data = op.outputs.local_data.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.