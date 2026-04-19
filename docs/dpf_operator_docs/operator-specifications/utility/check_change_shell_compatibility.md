---
category: utility
plugin: core
license: None
---

# utility:check change shell compatibility

**Version: 0.0.0**

## Description

Check if the shell layers of a shell layered field can be changed. Return true if the change can be done (for example, if field has TopBot and that the request is to change the shell layer to Top, then it will return true; if requesting to change the shell layer to Mid, it will return false).

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  target_e_shell_layer |[`int32`](../../core-concepts/dpf-types.md#standard-types), `enum dataProcessing::EShellLayers` | 0:Top, 1: Bottom, 2: TopBottom, 3: Mid are handled. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| change_validated |[`bool`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: check_change_shell_compatibility

 **Full name**: utility.check_change_shell_compatibility

 **Internal name**: check_change_shell_compatibility

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("check_change_shell_compatibility"); // operator instantiation
op.connect(0, my_field);
op.connect(1, my_target_e_shell_layer);
bool my_change_validated = op.getOutput<bool>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.check_change_shell_compatibility() # operator instantiation
op.inputs.field.connect(my_field)
op.inputs.target_e_shell_layer.connect(my_target_e_shell_layer)
my_change_validated = op.outputs.change_validated()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.check_change_shell_compatibility() # operator instantiation
op.inputs.field.Connect(my_field)
op.inputs.target_e_shell_layer.Connect(my_target_e_shell_layer)
my_change_validated = op.outputs.change_validated.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.