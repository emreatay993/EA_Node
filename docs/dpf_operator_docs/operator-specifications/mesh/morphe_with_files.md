---
category: mesh
plugin: N/A
license: None
---

# mesh:morphe with files

**Version: 0.0.0**

## Description

Computes the morphe field defined on a meshed region (in input 7) taking into account morphe settings written in .mf files. To be able to select a particular .mf file, the user needs to set up a string_field with the correspondence between time sets and file names (input 1) and pass a set of time sets (input 0). The output is a fields_container with label 'time' with one morphe field per time step in input 0.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  time_scoping |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`scoping`](../../core-concepts/dpf-types.md#scoping) | time steps to which morphing will be applied |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  time_to_mf |[`string_field`](../../core-concepts/dpf-types.md#string-field) | string_field defining, for each time set, the corresponding .mf file that defines its morphe field. Several time sets can correspond to the same .mf file. |
| <strong>Pin 7</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) | meshed region where morphe fields are defined. |
| <strong>Pin 8</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| morphe_fields |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: mesh

 **Plugin**: N/A

 **Scripting name**: morphe_with_files

 **Full name**: mesh.morphe_with_files

 **Internal name**: morph_field_from_files

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("morph_field_from_files"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(1, my_time_to_mf);
op.connect(7, my_mesh);
op.connect(8, my_time_freq_support);
ansys::dpf::FieldsContainer my_morphe_fields = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.mesh.morphe_with_files() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.time_to_mf.connect(my_time_to_mf)
op.inputs.mesh.connect(my_mesh)
op.inputs.time_freq_support.connect(my_time_freq_support)
my_morphe_fields = op.outputs.morphe_fields()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.mesh.morphe_with_files() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.time_to_mf.Connect(my_time_to_mf)
op.inputs.mesh.Connect(my_mesh)
op.inputs.time_freq_support.Connect(my_time_freq_support)
my_morphe_fields = op.outputs.morphe_fields.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.