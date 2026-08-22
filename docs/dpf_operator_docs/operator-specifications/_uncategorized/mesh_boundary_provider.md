---
category: None
plugin: core
license: None
---

# mesh boundary provider

**Version: 0.0.0**

## Description

Create a mesh boundary entity with a cmeshed region, a facets indices and facets types property fields.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  facet_indeces |[`property_field`](../../core-concepts/dpf-types.md#property-field) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  facet_types |[`property_field`](../../core-concepts/dpf-types.md#property-field) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  id |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 7</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| mesh_boundary |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: mesh_boundary_provider

 **Full name**: None

 **Internal name**: mesh::mesh_boundary_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mesh::mesh_boundary_provider"); // operator instantiation
op.connect(0, my_facet_indeces);
op.connect(1, my_facet_types);
op.connect(2, my_id);
op.connect(7, my_mesh);
ansys::dpf::MeshedRegion my_mesh_boundary = op.getOutput<ansys::dpf::MeshedRegion>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.mesh_boundary_provider() # operator instantiation
op.inputs.facet_indeces.connect(my_facet_indeces)
op.inputs.facet_types.connect(my_facet_types)
op.inputs.id.connect(my_id)
op.inputs.mesh.connect(my_mesh)
my_mesh_boundary = op.outputs.mesh_boundary()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.mesh_boundary_provider() # operator instantiation
op.inputs.facet_indeces.Connect(my_facet_indeces)
op.inputs.facet_types.Connect(my_facet_types)
op.inputs.id.Connect(my_id)
op.inputs.mesh.Connect(my_mesh)
my_mesh_boundary = op.outputs.mesh_boundary.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.