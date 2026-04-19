---
category: result
plugin: mapdl
license: any_dpf_supported_increments
---

# result:prns

**Version: 0.0.0**

## Description

write a filed into a prns equivalent format.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field |[`field`](../../core-concepts/dpf-types.md#field), [`fields_container`](../../core-concepts/dpf-types.md#fields-container) | field or fields container with only one field is expected |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  int_array |`class std::array<int,6>` | int array |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| scalar_int |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Integer |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: prns

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("prns"); // operator instantiation
op.connect(0, my_field);
op.connect(1, my_int_array);
int my_scalar_int = op.getOutput<int>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.field.connect(my_field)
op.inputs.int_array.connect(my_int_array)
my_scalar_int = op.outputs.scalar_int()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.field.Connect(my_field)
op.inputs.int_array.Connect(my_int_array)
my_scalar_int = op.outputs.scalar_int.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.