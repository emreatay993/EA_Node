---
category: utility
plugin: core
license: None
---

# utility:async buffer consumer

**Version: 0.0.0**

## Description

Synchronizes the outputs coming from the first thread to feed the second (2nd part: to connect to the consumer workflow).

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin -1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  num_iteration |[`int32`](../../core-concepts/dpf-types.md#standard-types) | starts at 0. |
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data |[`any`](../../core-concepts/dpf-types.md#any) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| data |[`any`](../../core-concepts/dpf-types.md#any) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **evaluate_inputs_before_run** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, all input pins of the operator will be evaluated before entering the run method to maintain a correct Operator status. |
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: async_buffer_consumer

 **Full name**: utility.async_buffer_consumer

 **Internal name**: async_buffer_consumer

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("async_buffer_consumer"); // operator instantiation
op.connect(-1, my_num_iteration);
op.connect(0, my_data);
ansys::dpf::Any my_data = op.getOutput<ansys::dpf::Any>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.async_buffer_consumer() # operator instantiation
op.inputs.num_iteration.connect(my_num_iteration)
op.inputs.data1.connect(my_data1)
op.inputs.data2.connect(my_data2)
my_data = op.outputs.data()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.async_buffer_consumer() # operator instantiation
op.inputs.num_iteration.Connect(my_num_iteration)
op.inputs.data.Connect(my_data)
my_data = op.outputs.data.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.