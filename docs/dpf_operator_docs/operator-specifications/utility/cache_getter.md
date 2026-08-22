---
category: utility
plugin: core
license: None
---

# utility:cache getter

**Version: 0.0.0**

## Description

Getter for caching information inside a workflow.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  output_pin_name |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |

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

 **Scripting name**: cache_getter

 **Full name**: utility.cache_getter

 **Internal name**: workflow::cache_getter

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::cache_getter"); // operator instantiation
op.connect(0, my_workflow);
op.connect(1, my_output_pin_name);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.cache_getter() # operator instantiation
op.inputs.workflow.connect(my_workflow)
op.inputs.output_pin_name.connect(my_output_pin_name)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.cache_getter() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
op.inputs.output_pin_name.Connect(my_output_pin_name)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.