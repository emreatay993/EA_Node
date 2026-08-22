---
category: server
plugin: grpc
license: None
---

# server:grpc remote workflow instantiate

**Version: 0.0.0**

## Description

Sends a local workflow to a remote process (and keep a local image of it) or create a local image of an existing remote workflow (identified by an id and an address) with a grpc streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow_to_send |[`workflow`](../../core-concepts/dpf-types.md#workflow), [`int32`](../../core-concepts/dpf-types.md#standard-types) | workflow to send |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  grpc_streams |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | dpf streams handling the server |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| remote_workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) | remote workflow containing an image of the remote workflow and the protocols streams |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: server

 **Plugin**: grpc

 **Scripting name**: grpc_remote_workflow_instantiate

 **Full name**: server.grpc_remote_workflow_instantiate

 **Internal name**: grpc::remote_workflow_instantiate

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("grpc::remote_workflow_instantiate"); // operator instantiation
op.connect(0, my_workflow_to_send);
op.connect(3, my_grpc_streams);
ansys::dpf::Workflow my_remote_workflow = op.getOutput<ansys::dpf::Workflow>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.server.grpc_remote_workflow_instantiate() # operator instantiation
op.inputs.workflow_to_send.connect(my_workflow_to_send)
op.inputs.grpc_streams.connect(my_grpc_streams)
my_remote_workflow = op.outputs.remote_workflow()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.server.grpc_remote_workflow_instantiate() # operator instantiation
op.inputs.workflow_to_send.Connect(my_workflow_to_send)
op.inputs.grpc_streams.Connect(my_grpc_streams)
my_remote_workflow = op.outputs.remote_workflow.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.