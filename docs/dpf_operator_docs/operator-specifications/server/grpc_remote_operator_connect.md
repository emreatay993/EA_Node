---
category: server
plugin: grpc
license: None
---

# server:grpc remote operator connect

**Version: 0.0.0**

## Description

Creates a CRemoteOperator instance of the input CRemoteOperator or COperator (on 3) on the remote where the Operator (on 0) is located and call "connect" from this remote with grpc.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_operator_to_connect_with |[`operator`](../../core-concepts/dpf-types.md#operator) | grpc remote operator |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_operator |[`operator`](../../core-concepts/dpf-types.md#operator) | grpc remote operator |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: server

 **Plugin**: grpc

 **Scripting name**: grpc_remote_operator_connect

 **Full name**: server.grpc_remote_operator_connect

 **Internal name**: grpc::remote_operator_connect

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("grpc::remote_operator_connect"); // operator instantiation
op.connect(0, my_remote_operator_to_connect_with);
op.connect(3, my_remote_operator);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.server.grpc_remote_operator_connect() # operator instantiation
op.inputs.remote_operator_to_connect_with.connect(my_remote_operator_to_connect_with)
op.inputs.remote_operator.connect(my_remote_operator)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.server.grpc_remote_operator_connect() # operator instantiation
op.inputs.remote_operator_to_connect_with.Connect(my_remote_operator_to_connect_with)
op.inputs.remote_operator.Connect(my_remote_operator)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.