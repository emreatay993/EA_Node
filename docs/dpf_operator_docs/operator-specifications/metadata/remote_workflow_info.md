---
category: metadata
plugin: core
license: None
---

# metadata:remote workflow info provider

**Version: 0.0.0**

## Description

Collect information (list of input and outputs pins) on a remote workflow for a given protocol registered in the streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_workflow |[`remote_workflow`](../../core-concepts/dpf-types.md#remote-workflow) |  |
| <strong>Pin 200</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  get_operators |[`bool`](../../core-concepts/dpf-types.md#standard-types) | If true, the remote operators with their exposed input and output pin numbers are returned (default is false) |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| input_pins |[`vector<string>`](../../core-concepts/dpf-types.md#standard-types) |  |
|  **Pin 1**| output_pins |[`vector<string>`](../../core-concepts/dpf-types.md#standard-types) |  |
|  **Pin 2**| exposed_input_operators |[`operator`](../../core-concepts/dpf-types.md#operator) |  |
|  **Pin 3**| exposed_input_pin |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: remote_workflow_info

 **Full name**: metadata.remote_workflow_info

 **Internal name**: remote_workflow_info

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("remote_workflow_info"); // operator instantiation
op.connect(3, my_remote_workflow);
op.connect(200, my_get_operators);
std::vector<std::string> my_input_pins = op.getOutput<std::vector<std::string>>(0);
std::vector<std::string> my_output_pins = op.getOutput<std::vector<std::string>>(1);
ansys::dpf::Operator my_exposed_input_operators = op.getOutput<ansys::dpf::Operator>(2);
int my_exposed_input_pin = op.getOutput<int>(3);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.remote_workflow_info() # operator instantiation
op.inputs.remote_workflow.connect(my_remote_workflow)
op.inputs.get_operators.connect(my_get_operators)
my_input_pins = op.outputs.input_pins()
my_output_pins = op.outputs.output_pins()
my_exposed_input_operators = op.outputs.exposed_input_operators()
my_exposed_input_pin = op.outputs.exposed_input_pin()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.remote_workflow_info() # operator instantiation
op.inputs.remote_workflow.Connect(my_remote_workflow)
op.inputs.get_operators.Connect(my_get_operators)
my_input_pins = op.outputs.input_pins.GetData()
my_output_pins = op.outputs.output_pins.GetData()
my_exposed_input_operators = op.outputs.exposed_input_operators.GetData()
my_exposed_input_pin = op.outputs.exposed_input_pin.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.