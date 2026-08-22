---
category: metadata
plugin: core
license: None
---

# metadata:mapdl::rst::V_cyclic

**Version: 0.0.0**

## Description

This operator is deprecated: use the operator nodal velocities with the read_cyclic pin instead. Read nodal velocities from a result file and expand it with cyclic symmetry.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  time_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 1</strong>|  mesh_scoping |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 2</strong>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | FieldsContainer already allocated modified inplace |
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container), `stream` | Streams containing the result file. |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | data sources containing the result file. |
| <strong>Pin 5</strong>|  bool_rotate_to_global |[`bool`](../../core-concepts/dpf-types.md#standard-types) | if true the field is rotated to global coordinate system (default true) |
| <strong>Pin 6</strong>|  all_dofs |[`bool`](../../core-concepts/dpf-types.md#standard-types) | if this pin is set to true, all the dofs are retrieved. By default this pin is set to false and only the translational dofs are retrieved. |
| <strong>Pin 7</strong>|  sector_mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region), [`meshes_container`](../../core-concepts/dpf-types.md#meshes-container) | mesh of the base sector (can be a skin). |
| <strong>Pin 9</strong>|  requested_location |[`string`](../../core-concepts/dpf-types.md#standard-types) | location needed in output |
| <strong>Pin 14</strong>|  read_cyclic |`enum dataProcessing::ECyclicReading`, [`int32`](../../core-concepts/dpf-types.md#standard-types) | if 0 cyclic symmetry is ignored, if 1 cyclic sector is read, if 2 cyclic expansion is done, if 3 cyclic expansion is done and stages are merged (default is 1) |
| <strong>Pin 15</strong>|  expanded_meshed_region |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region), [`meshes_container`](../../core-concepts/dpf-types.md#meshes-container) | mesh expanded. |
| <strong>Pin 16</strong>|  cyclic_support |[`cyclic_support`](../../core-concepts/dpf-types.md#cyclic-support) |  |
| <strong>Pin 18</strong>|  sectors_to_expand |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | sectors to expand (start at 0), for multistage: use scopings container with 'stage' label. |
| <strong>Pin 19</strong>|  phi |[`double`](../../core-concepts/dpf-types.md#standard-types) | angle phi in degrees (default value 0.0) |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | FieldsContainer filled in |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |
| **use_cache** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Some intermediate data is put in cache if this config is set to true. This option can reduce computation time after the first run. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::rst::V_cyclic

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rst::V_cyclic"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(1, my_mesh_scoping);
op.connect(2, my_fields_container);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(5, my_bool_rotate_to_global);
op.connect(6, my_all_dofs);
op.connect(7, my_sector_mesh);
op.connect(9, my_requested_location);
op.connect(14, my_read_cyclic);
op.connect(15, my_expanded_meshed_region);
op.connect(16, my_cyclic_support);
op.connect(18, my_sectors_to_expand);
op.connect(19, my_phi);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.mesh_scoping.connect(my_mesh_scoping)
op.inputs.fields_container.connect(my_fields_container)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.bool_rotate_to_global.connect(my_bool_rotate_to_global)
op.inputs.all_dofs.connect(my_all_dofs)
op.inputs.sector_mesh.connect(my_sector_mesh)
op.inputs.requested_location.connect(my_requested_location)
op.inputs.read_cyclic.connect(my_read_cyclic)
op.inputs.expanded_meshed_region.connect(my_expanded_meshed_region)
op.inputs.cyclic_support.connect(my_cyclic_support)
op.inputs.sectors_to_expand.connect(my_sectors_to_expand)
op.inputs.phi.connect(my_phi)
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.mesh_scoping.Connect(my_mesh_scoping)
op.inputs.fields_container.Connect(my_fields_container)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.bool_rotate_to_global.Connect(my_bool_rotate_to_global)
op.inputs.all_dofs.Connect(my_all_dofs)
op.inputs.sector_mesh.Connect(my_sector_mesh)
op.inputs.requested_location.Connect(my_requested_location)
op.inputs.read_cyclic.Connect(my_read_cyclic)
op.inputs.expanded_meshed_region.Connect(my_expanded_meshed_region)
op.inputs.cyclic_support.Connect(my_cyclic_support)
op.inputs.sectors_to_expand.Connect(my_sectors_to_expand)
op.inputs.phi.Connect(my_phi)
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.