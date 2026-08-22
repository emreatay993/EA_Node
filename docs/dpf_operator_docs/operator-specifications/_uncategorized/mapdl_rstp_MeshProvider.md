---
category: None
plugin: mapdl
license: None
---

# mapdl mesh provider

**Version: 0.0.0**

## Description

Reads a mesh from result files

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin -1</strong>|  clear_mesh_cache |[`bool`](../../core-concepts/dpf-types.md#standard-types) | if true, the cached mesh is cleared before leaving the operator, even if streams are used (default is false) |
| <strong>Pin 0</strong>|  time_scoping |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Optional time/frequency set ID of the mesh, supported for adaptative meshes |
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | result file container allowed to be kept open to cache data |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | result file path container, used if no streams are set |
| <strong>Pin 14</strong>|  read_cyclic |`enum dataProcessing::ECyclicReading`, [`int32`](../../core-concepts/dpf-types.md#standard-types) | if 1 cyclic symmetry is ignored, if 2 cyclic expansion is done (default is 1) |
| <strong>Pin 200</strong>|  laziness |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) | configurate whether lazy evaluation can be performed and to what extent. Supported attributes are: <br>- "num_named_selections"->num named selection to read (-1 is all, int32, default si -1), carefull: the other named selections will not be available, use mesh_property_provider Operator to read them.<br>- "unsupported_apdl_element_type"-> if set to 1, the property field "unsupported_apdl_element_type" will be attached to the mesh and list elements that were skipped when reading the mesh. This property is not available through mesh_property_provider.<br>- all mesh property fields "mat", "named_selection", "apdl_element_type", "section"-> if set to 1 these properties will not be read and a workflow will be bounded to the properties to be evaluated on demand, with 0 they are read (default is 0).<br>- "all_available_properties" option set to 0 will return all possible properties |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::rstp::MeshProvider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rstp::MeshProvider"); // operator instantiation
op.connect(-1, my_clear_mesh_cache);
op.connect(0, my_time_scoping);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(14, my_read_cyclic);
op.connect(200, my_laziness);
ansys::dpf::MeshedRegion my_mesh = op.getOutput<ansys::dpf::MeshedRegion>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.clear_mesh_cache.connect(my_clear_mesh_cache)
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.read_cyclic.connect(my_read_cyclic)
op.inputs.laziness.connect(my_laziness)
my_mesh = op.outputs.mesh()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.clear_mesh_cache.Connect(my_clear_mesh_cache)
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.read_cyclic.Connect(my_read_cyclic)
op.inputs.laziness.Connect(my_laziness)
my_mesh = op.outputs.mesh.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.