---
category: server
plugin: grpc
license: None
---

# server:grpc remote workflow release

**Version: 0.0.0**

## Description

Release a remote workflow for a given protocol registered in the streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) | grpc remote workflow |

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

 **Scripting name**: grpc_remote_workflow_release

 **Full name**: server.grpc_remote_workflow_release

 **Internal name**: grpc::remote_workflow_release

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("grpc::remote_workflow_release"); // operator instantiation
op.connect(3, my_remote_workflow);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.server.grpc_remote_workflow_release() # operator instantiation
op.inputs.remote_workflow.connect(my_remote_workflow)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.server.grpc_remote_workflow_release() # operator instantiation
op.inputs.remote_workflow.Connect(my_remote_workflow)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.