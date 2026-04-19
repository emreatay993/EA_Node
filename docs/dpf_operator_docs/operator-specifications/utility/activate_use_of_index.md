---
category: utility
plugin: core
license: None
---

# utility:activate use of index

**Version: 0.0.0**

## Description

Enable the use of the global workflow step index.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |

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

 **Scripting name**: activate_use_of_index

 **Full name**: utility.activate_use_of_index

 **Internal name**: workflow::index_setter

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::index_setter"); // operator instantiation
op.connect(0, my_workflow);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.activate_use_of_index() # operator instantiation
op.inputs.workflow.connect(my_workflow)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.activate_use_of_index() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.