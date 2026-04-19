---
category: server
plugin: grpc
license: None
---

# server:grpc remote_workflow_get_status

**Version: 0.0.0**

## Description

Returns the status of a remote operator with a grpc streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_operator |[`operator`](../../core-concepts/dpf-types.md#operator) | grpc remote operator |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| status |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: server

 **Plugin**: grpc

 **Scripting name**: grpc_remote_workflow_get_status

 **Full name**: server.grpc_remote_workflow_get_status

 **Internal name**: grpc::remote_operator_get_status

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("grpc::remote_operator_get_status"); // operator instantiation
op.connect(3, my_remote_operator);
int my_status = op.getOutput<int>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.server.grpc_remote_workflow_get_status() # operator instantiation
op.inputs.remote_operator.connect(my_remote_operator)
my_status = op.outputs.status()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.server.grpc_remote_workflow_get_status() # operator instantiation
op.inputs.remote_operator.Connect(my_remote_operator)
my_status = op.outputs.status.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.