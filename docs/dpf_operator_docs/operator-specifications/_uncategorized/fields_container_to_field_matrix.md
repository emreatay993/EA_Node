---
category: None
plugin: N/A
license: None
---

# fields_container_to_field_matrix

**Version: 0.0.0**

## Description



## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container), [`field`](../../core-concepts/dpf-types.md#field) | fields container to convertThe input fields_container must not contain duplicate label_spaces. |
| <strong>Pin 1</strong>|  column_label |[`string`](../../core-concepts/dpf-types.md#standard-types) | label to use as combined columns. Default is none. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| matrix |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Field matrix containing the data from the fields container. It will be complex if the input was complex. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: fields_container_to_field_matrix

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("fields_container_to_field_matrix"); // operator instantiation
op.connect(0, my_fields_container);
op.connect(1, my_column_label);
ansys::dpf::CustomTypeField my_matrix = op.getOutput<ansys::dpf::CustomTypeField>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.fields_container.connect(my_fields_container)
op.inputs.column_label.connect(my_column_label)
my_matrix = op.outputs.matrix()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.fields_container.Connect(my_fields_container)
op.inputs.column_label.Connect(my_column_label)
my_matrix = op.outputs.matrix.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.