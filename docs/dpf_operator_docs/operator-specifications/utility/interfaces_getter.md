---
category: utility
plugin: core
license: None
---

# utility:interfaces getter

**Version: 0.0.0**

## Description

Getter for interfaces inside a workflow.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| interfaces |[`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: interfaces_getter

 **Full name**: utility.interfaces_getter

 **Internal name**: workflow::interface_getter

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("workflow::interface_getter"); // operator instantiation
op.connect(0, my_workflow);
ansys::dpf::GenericDataContainer my_interfaces = op.getOutput<ansys::dpf::GenericDataContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.interfaces_getter() # operator instantiation
op.inputs.workflow.connect(my_workflow)
my_interfaces = op.outputs.interfaces()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.interfaces_getter() # operator instantiation
op.inputs.workflow.Connect(my_workflow)
my_interfaces = op.outputs.interfaces.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.