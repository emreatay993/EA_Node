---
category: result
plugin: mapdl
license: None
---

# result:mapdl::rst::ECT_STAT

**Version: 0.0.0**

## Description

Read element contact status from rst file.

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
| <strong>Pin 7</strong>|  mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |
| <strong>Pin 14</strong>|  read_cyclic |`enum dataProcessing::ECyclicReading`, [`int32`](../../core-concepts/dpf-types.md#standard-types) | if 0 cyclic symmetry is ignored, if 1 cyclic sector is read, if 2 cyclic expansion is done, if 3 cyclic expansion is done and stages are merged (default is 1) |
| <strong>Pin 20</strong>|  filter_degenerated_elements |[`bool`](../../core-concepts/dpf-types.md#standard-types) | if set to true, results are filtered to handle degenerated elements (default is true) |
| <strong>Pin 200</strong>|  tunning |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) | DataTree that can contain: int attribute 'ReadResultsAtCentroids' with 0, 1 or 2 value (0 won't read, 1 will force read, 2 is default and will read only if results are detected). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | FieldsContainer filled in |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::rst::ECT_STAT

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rst::ECT_STAT"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(1, my_mesh_scoping);
op.connect(2, my_fields_container);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(5, my_bool_rotate_to_global);
op.connect(6, my_all_dofs);
op.connect(7, my_mesh);
op.connect(14, my_read_cyclic);
op.connect(20, my_filter_degenerated_elements);
op.connect(200, my_tunning);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.mesh_scoping.connect(my_mesh_scoping)
op.inputs.fields_container.connect(my_fields_container)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.bool_rotate_to_global.connect(my_bool_rotate_to_global)
op.inputs.all_dofs.connect(my_all_dofs)
op.inputs.mesh.connect(my_mesh)
op.inputs.read_cyclic.connect(my_read_cyclic)
op.inputs.filter_degenerated_elements.connect(my_filter_degenerated_elements)
op.inputs.tunning.connect(my_tunning)
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.mesh_scoping.Connect(my_mesh_scoping)
op.inputs.fields_container.Connect(my_fields_container)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.bool_rotate_to_global.Connect(my_bool_rotate_to_global)
op.inputs.all_dofs.Connect(my_all_dofs)
op.inputs.mesh.Connect(my_mesh)
op.inputs.read_cyclic.Connect(my_read_cyclic)
op.inputs.filter_degenerated_elements.Connect(my_filter_degenerated_elements)
op.inputs.tunning.Connect(my_tunning)
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.