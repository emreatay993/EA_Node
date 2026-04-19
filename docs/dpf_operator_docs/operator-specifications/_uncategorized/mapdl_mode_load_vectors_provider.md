---
category: None
plugin: core
license: None
---

# mapdl::mode::load_vectors_provider

**Version: 0.0.0**

## Description

Retrieve nodal load vectors from mode file.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  time_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) |  |
| <strong>Pin 1</strong>|  mesh_scoping |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) |  |
| <strong>Pin 6</strong>|  vector<int32> |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 12</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  is_harmonic |[`bool`](../../core-concepts/dpf-types.md#standard-types) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::mode::load_vectors_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::mode::load_vectors_provider"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(1, my_mesh_scoping);
op.connect(3, my_streams_container);
op.connect(6, my_vector<int32>);
op.connect(12, my_is_harmonic);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.mesh_scoping.connect(my_mesh_scoping)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.vector<int32>.connect(my_vector<int32>)
op.inputs.is_harmonic.connect(my_is_harmonic)
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.mesh_scoping.Connect(my_mesh_scoping)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.vector<int32>.Connect(my_vector<int32>)
op.inputs.is_harmonic.Connect(my_is_harmonic)
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.