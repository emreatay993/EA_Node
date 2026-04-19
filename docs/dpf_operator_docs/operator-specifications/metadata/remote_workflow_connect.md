---
category: metadata
plugin: core
license: None
---

# metadata:remote workflow connect

**Version: 0.0.0**

## Description

Creates a CRemoteWorkflow instance of the input CRemoteWorkflow or Workflow (on 3) on the remote where the Worflow (on 0) is located and call chain With from this remote for a given protocol registered in the streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  left_remote_workflow |[`remote_workflow`](../../core-concepts/dpf-types.md#remote-workflow), [`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
| <strong>Pin 1</strong>|  outputs |[`vector<string>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 2</strong>|  inputs |[`vector<string>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  right_remote_workflow |[`remote_workflow`](../../core-concepts/dpf-types.md#remote-workflow) |  |

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

 **Scripting name**: remote_workflow_connect

 **Full name**: metadata.remote_workflow_connect

 **Internal name**: remote_workflow_connect

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("remote_workflow_connect"); // operator instantiation
op.connect(0, my_left_remote_workflow);
op.connect(1, my_outputs);
op.connect(2, my_inputs);
op.connect(3, my_right_remote_workflow);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.remote_workflow_connect() # operator instantiation
op.inputs.left_remote_workflow.connect(my_left_remote_workflow)
op.inputs.outputs.connect(my_outputs)
op.inputs.inputs.connect(my_inputs)
op.inputs.right_remote_workflow.connect(my_right_remote_workflow)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.remote_workflow_connect() # operator instantiation
op.inputs.left_remote_workflow.Connect(my_left_remote_workflow)
op.inputs.outputs.Connect(my_outputs)
op.inputs.inputs.Connect(my_inputs)
op.inputs.right_remote_workflow.Connect(my_right_remote_workflow)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.