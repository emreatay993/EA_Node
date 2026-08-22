---
category: server
plugin: grpc
license: None
---

# server:grpc remote data receiver

**Version: 0.0.0**

## Description

Returns the output data on a given pin name of a remote workflow locally with a grpc streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_workflow_output_name |[`string`](../../core-concepts/dpf-types.md#standard-types) | name of the remote workflow output to chain to the local workflow |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) | grpc remote workflow |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 1**| local_data |[`any`](../../core-concepts/dpf-types.md#any) | what was in output of remote workflow |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **allow_reverse_grpc_connection** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | -1 | If this option is set to 1, a new gRPC channel is created to reverse client->server connections (to become server->client). This allows to push data more efficiently. If -1 it default to the runtime dpf core config. |
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: server

 **Plugin**: grpc

 **Scripting name**: grpc_remote_data_receiver

 **Full name**: server.grpc_remote_data_receiver

 **Internal name**: grpc::remote_data_receiver

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("grpc::remote_data_receiver"); // operator instantiation
op.connect(1, my_remote_workflow_output_name);
op.connect(3, my_remote_workflow);
ansys::dpf::Any my_local_data = op.getOutput<ansys::dpf::Any>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.server.grpc_remote_data_receiver() # operator instantiation
op.inputs.remote_workflow_output_name.connect(my_remote_workflow_output_name)
op.inputs.remote_workflow.connect(my_remote_workflow)
my_local_data = op.outputs.local_data()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.server.grpc_remote_data_receiver() # operator instantiation
op.inputs.remote_workflow_output_name.Connect(my_remote_workflow_output_name)
op.inputs.remote_workflow.Connect(my_remote_workflow)
my_local_data = op.outputs.local_data.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.