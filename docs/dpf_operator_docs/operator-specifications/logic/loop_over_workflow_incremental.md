---
category: logic
plugin: core
license: None
---

# logic:loop over workflow incremental

**Version: 0.0.0**

## Description

Loop over the number of ellipsis pin (from pin 3) and for each of these inputs connect the input to the workflow, evaluate the workfow and merge the results into a fields container for each iteration

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  input_name |[`string`](../../core-concepts/dpf-types.md#standard-types) | name of the workflow's input pin to loop over |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  output_names |[`vector<string>`](../../core-concepts/dpf-types.md#standard-types) | name of the workflow's output pins, for each iteration of the loop, the output is stored in the output fields container |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  inputs_to_connect |[`any`](../../core-concepts/dpf-types.md#any) | all the inputs (from pin 3 to infinity) to connect to the workflow in input name pin 1 |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | the number of outputs is equal to the number of output names |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: logic

 **Plugin**: core

 **Scripting name**: loop_over_workflow_incremental

 **Full name**: logic.loop_over_workflow_incremental

 **Internal name**: loop_over_workflow_incremental

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("loop_over_workflow_incremental"); // operator instantiation
op.connect(0, my_workflow);
op.connect(1, my_input_name);
op.connect(2, my_output_names);
op.connect(3, my_inputs_to_connect);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.logic.loop_over_workflow_incremental() # operator instantiation
op.inputs.workflow.connect(my_workflow)
op.inputs.input_name.connect(my_input_name)
op.inputs.output_names.connect(my_output_names)
op.inputs.inputs_to_connect1.connect(my_inputs_to_connect1)
op.inputs.inputs_to_connect2.connect(my_inputs_to_connect2)
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.logic.loop_over_workflow_incremental() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
op.inputs.input_name.Connect(my_input_name)
op.inputs.output_names.Connect(my_output_names)
op.inputs.inputs_to_connect.Connect(my_inputs_to_connect)
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.