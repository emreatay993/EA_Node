---
category: utility
plugin: core
license: None
---

# utility:strategy setter

**Version: 0.0.0**

## Description

Setter for workflow strategy.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  strategy_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: strategy_setter

 **Full name**: utility.strategy_setter

 **Internal name**: workflow::strategy_setter

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::strategy_setter"); // operator instantiation
op.connect(0, my_workflow);
op.connect(1, my_strategy_id);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.strategy_setter() # operator instantiation
op.inputs.workflow.connect(my_workflow)
op.inputs.strategy_id.connect(my_strategy_id)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.strategy_setter() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
op.inputs.strategy_id.Connect(my_strategy_id)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.