---
category: result
plugin: N/A
license: None
---

# result:cff::flprj::Y

**Version: 0.0.0**

## Description

Reads/computes Mass Fraction from result streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  time_scoping |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | time ids required in output |
| <strong>Pin 1</strong>|  mesh_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping), [`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | nodes or elements scoping required in output. The output fields will be scoped on these node or element IDs. To figure out the ordering of the fields data, look at their scoping IDs as they might not be ordered as the input scoping was. The scoping's location indicates whether nodes or elements are asked for. |
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | result file container allowed to be kept open to cache data |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | result file path container, used if no streams are set |
| <strong>Pin 7</strong>|  mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region), [`meshes_container`](../../core-concepts/dpf-types.md#meshes-container) | prevents from reading the mesh in the result files. |
| <strong>Pin 25</strong>|  zone_id |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`scoping`](../../core-concepts/dpf-types.md#scoping) | zone id (integer) or vector of zone ids (vector) or zone scoping (scoping) |
| <strong>Pin 1000</strong>|  results_qualifiers |[`label_space`](../../core-concepts/dpf-types.md#label-space) | LabelSpace with combination of zone, phases or species IDs |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| mass_fraction |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | mass_fraction |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: N/A

 **Scripting name**: mass_fraction

 **Full name**: result.mass_fraction

 **Internal name**: cff::flprj::Y

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cff::flprj::Y"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(1, my_mesh_scoping);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(7, my_mesh);
op.connect(25, my_zone_id);
op.connect(1000, my_results_qualifiers);
ansys::dpf::FieldsContainer my_mass_fraction = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.mass_fraction() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.mesh_scoping.connect(my_mesh_scoping)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.mesh.connect(my_mesh)
op.inputs.zone_id.connect(my_zone_id)
op.inputs.results_qualifiers1.connect(my_results_qualifiers1)
op.inputs.results_qualifiers2.connect(my_results_qualifiers2)
my_mass_fraction = op.outputs.mass_fraction()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.mass_fraction() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.mesh_scoping.Connect(my_mesh_scoping)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.mesh.Connect(my_mesh)
op.inputs.zone_id.Connect(my_zone_id)
op.inputs.results_qualifiers.Connect(my_results_qualifiers)
my_mass_fraction = op.outputs.mass_fraction.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.