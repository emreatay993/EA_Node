---
category: mapping
plugin: N/A
license: None
---

# mapping:sc_apply_mapping

**Version: 0.0.0**

## Description

Maps input data with precomputed data.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  sc_counter | | sc counter to keep track |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  source_scoping |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | Source scoping |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  target_scoping |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | Target scoping |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  source_data |[`field`](../../core-concepts/dpf-types.md#field), [`fields_container`](../../core-concepts/dpf-types.md#fields-container) | data to be mapped. |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  target_meshes |[`meshes_container`](../../core-concepts/dpf-types.md#meshes-container) | data to be mapped. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| target_data |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | data mapped on the target mesh/coords |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: mapping

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: sc_apply_mapping

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("sc_apply_mapping"); // operator instantiation
op.connect(0, my_sc_counter);
op.connect(1, my_source_scoping);
op.connect(2, my_target_scoping);
op.connect(3, my_source_data);
op.connect(4, my_target_meshes);
ansys::dpf::FieldsContainer my_target_data = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.mapping.None() # operator instantiation
op.inputs.sc_counter.connect(my_sc_counter)
op.inputs.source_scoping.connect(my_source_scoping)
op.inputs.target_scoping.connect(my_target_scoping)
op.inputs.source_data.connect(my_source_data)
op.inputs.target_meshes.connect(my_target_meshes)
my_target_data = op.outputs.target_data()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.mapping.None() # operator instantiation
op.inputs.sc_counter.Connect(my_sc_counter)
op.inputs.source_scoping.Connect(my_source_scoping)
op.inputs.target_scoping.Connect(my_target_scoping)
op.inputs.source_data.Connect(my_source_data)
op.inputs.target_meshes.Connect(my_target_meshes)
my_target_data = op.outputs.target_data.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.