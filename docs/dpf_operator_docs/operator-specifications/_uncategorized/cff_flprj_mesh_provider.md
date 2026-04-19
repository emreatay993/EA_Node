---
category: None
plugin: N/A
license: None
---

# cff::flprj::mesh_provider

**Version: 0.0.0**

## Description

Read mesh from result streams. Mesh can be spatially or temporally varying.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  time_scoping |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`int32`](../../core-concepts/dpf-types.md#standard-types) | time id (integer) or vector with a single time id (vector) required in output |
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | result file container allowed to be kept open to cache data |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | result file path container, used if no streams are set |
| <strong>Pin 25</strong>|  zone_id |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | zone id (integer) or vector with a single zone id (vector) or scoping with a single zone id (scoping) or a scopings_container on zones and partitions with scopings on cells coming from different zones (scopings_container) |
| <strong>Pin 200</strong>|  laziness |[`data_tree`](../../core-concepts/dpf-types.md#data-tree) | Configure mesh properties evaluation laziness via a DataTree.<br>Each entry in the DataTree will dictate behavior for one or more mesh properties as follows:<br>- if an entry is set to 0, it is read with the mesh.- if an entry is set to 1, it is not read with the mesh and is evaluated on demand.- some entries propose other options defined in their specific descriptions.- the 'all_available_properties' entry overrides all others and can be set to either 0 or 1.Available entries and options for a Fluent mesh are:- 'cell_zone_id'=0/1 (default 1)- 'face_zone_id'=0/1 (default 1) |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region), [`meshes_container`](../../core-concepts/dpf-types.md#meshes-container) | meshed region |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cff::flprj::mesh_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cff::flprj::mesh_provider"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(25, my_zone_id);
op.connect(200, my_laziness);
ansys::dpf::MeshedRegion my_mesh = op.getOutput<ansys::dpf::MeshedRegion>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.zone_id.connect(my_zone_id)
op.inputs.laziness.connect(my_laziness)
my_mesh_as_abstract_meshed_region = op.outputs.mesh_as_abstract_meshed_region()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.zone_id.Connect(my_zone_id)
op.inputs.laziness.Connect(my_laziness)
my_mesh = op.outputs.mesh.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.