---
category: server
plugin: grpc
license: None
---

# server:grpc remote workflow info provider

**Version: 0.0.0**

## Description

Collect information (list of input and outputs pins) on a remote workflow with a grpc streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) | grpc remote workflow |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| output_pins | |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: server

 **Plugin**: grpc

 **Scripting name**: grpc_remote_workflow_info

 **Full name**: server.grpc_remote_workflow_info

 **Internal name**: grpc::remote_workflow_info

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("grpc::remote_workflow_info"); // operator instantiation
op.connect(3, my_remote_workflow);
 my_output_pins = op.getOutput<>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.server.grpc_remote_workflow_info() # operator instantiation
op.inputs.remote_workflow.connect(my_remote_workflow)
my_output_pins = op.outputs.output_pins()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.server.grpc_remote_workflow_info() # operator instantiation
op.inputs.remote_workflow.Connect(my_remote_workflow)
my_output_pins = op.outputs.output_pins.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.