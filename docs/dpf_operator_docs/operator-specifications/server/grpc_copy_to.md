---
category: server
plugin: grpc
license: None
---

# server:grpc::copy_to

**Version: 0.0.0**

## Description

Makes a deep copy of any local data in input on a gRPC client. The created remote entity is then recorded in the remote gRPC database (the database keeps ownership of the created data). The ID of the recorded entity and the identifier of the remote database are returned.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data |[`any`](../../core-concepts/dpf-types.md#any) | Local instance of any DPF supported type to copy. |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  grpc_streams |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | dpf streams or data sources allowing to connect to the server |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | ID of the created entity in the database. |
|  **Pin 1**| database_identifier |[`string`](../../core-concepts/dpf-types.md#standard-types) | Name of the database. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: server

 **Plugin**: grpc

 **Scripting name**: None

 **Full name**: None

 **Internal name**: grpc::copy_to

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("grpc::copy_to"); // operator instantiation
op.connect(0, my_data);
op.connect(3, my_grpc_streams);
int my_id = op.getOutput<int>(0);
std::string my_database_identifier = op.getOutput<std::string>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.server.None() # operator instantiation
op.inputs.data.connect(my_data)
op.inputs.grpc_streams.connect(my_grpc_streams)
my_id = op.outputs.id()
my_database_identifier = op.outputs.database_identifier()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.server.None() # operator instantiation
op.inputs.data.Connect(my_data)
op.inputs.grpc_streams.Connect(my_grpc_streams)
my_id = op.outputs.id.GetData()
my_database_identifier = op.outputs.database_identifier.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.