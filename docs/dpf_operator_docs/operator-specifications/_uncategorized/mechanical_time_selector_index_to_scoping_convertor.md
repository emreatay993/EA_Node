---
category: None
plugin: N/A
license: None
---

# mechanical::time_selector_index_to_scoping_convertor

**Version: 0.0.0**

## Description

convert the integer index input to CScoping id input for operator mechanical::time_selector

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  time_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping), [`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mechanical::time_selector_index_to_scoping_convertor

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical::time_selector_index_to_scoping_convertor"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(1, my_fields_container);
ansys::dpf::Scoping my_scoping = op.getOutput<ansys::dpf::Scoping>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.fields_container.connect(my_fields_container)
my_scoping = op.outputs.scoping()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.fields_container.Connect(my_fields_container)
my_scoping = op.outputs.scoping.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.