---
category: logic
plugin: core
license: None
---

# logic:if contains name

**Version: 0.0.0**

## Description

Evaluates operator from pin 2 input if list of strings (pin1) contains input string (pin0) Otherwise, it evaluates pin 3.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  name |[`string`](../../core-concepts/dpf-types.md#standard-types) | Input name |
| <strong>Pin 1</strong>|  list_names |[`vector<string>`](../../core-concepts/dpf-types.md#standard-types), [`string`](../../core-concepts/dpf-types.md#standard-types) | List of names to check. If not provided, output will be pin 2. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  if_true |[`operator`](../../core-concepts/dpf-types.md#operator) | Operator to evaluate if true. |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  if_false |[`operator`](../../core-concepts/dpf-types.md#operator) | Operator to evaluate if false. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| output |[`any`](../../core-concepts/dpf-types.md#any) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: logic

 **Plugin**: core

 **Scripting name**: if_contains_name

 **Full name**: logic.if_contains_name

 **Internal name**: logic::if_contains_name

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("logic::if_contains_name"); // operator instantiation
op.connect(0, my_name);
op.connect(1, my_list_names);
op.connect(2, my_if_true);
op.connect(3, my_if_false);
ansys::dpf::Any my_output = op.getOutput<ansys::dpf::Any>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.logic.if_contains_name() # operator instantiation
op.inputs.name.connect(my_name)
op.inputs.list_names.connect(my_list_names)
op.inputs.if_true.connect(my_if_true)
op.inputs.if_false.connect(my_if_false)
my_output = op.outputs.output()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.logic.if_contains_name() # operator instantiation
op.inputs.name.Connect(my_name)
op.inputs.list_names.Connect(my_list_names)
op.inputs.if_true.Connect(my_if_true)
op.inputs.if_false.Connect(my_if_false)
my_output = op.outputs.output.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.