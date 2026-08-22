---
category: metadata
plugin: cgns
license: None
---

# metadata:mesh info provider

**Version: 0.0.0**

## Description

Reads the mesh information, such as number of elements (common property), number of faces (Cff plugins) or scoping of parts (LSDYNA plugins) on files contained in the streams or data sources.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  time_scoping |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Optional time/frequency set ID of the mesh. |
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | streams (mesh file container) (optional) |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | If the stream is null, retrieves the file path from the data sources. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| mesh_info |[`mesh_info`](../../core-concepts/dpf-types.md#mesh-info) |   |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: metadata

 **Plugin**: cgns

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cgns::cgns::mesh_info_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cgns::cgns::mesh_info_provider"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
ansys::dpf::MeshInfo my_mesh_info = op.getOutput<ansys::dpf::MeshInfo>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
my_mesh_info = op.outputs.mesh_info()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
my_mesh_info = op.outputs.mesh_info.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.