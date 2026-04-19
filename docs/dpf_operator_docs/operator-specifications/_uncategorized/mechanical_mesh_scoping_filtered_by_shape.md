---
category: None
plugin: N/A
license: None
---

# mechanical mesh scoping filtered by shape

**Version: 0.0.0**

## Description

Provides a scoping from given shape. Several shapes can be asked at the same time.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  requested_location |[`string`](../../core-concepts/dpf-types.md#standard-types) | Nodal or Elemental location are expected |
| <strong>Pin 1</strong>|  property_id |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 7</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| mesh_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) | Scoping |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: mechanical_mesh_scoping_filtered_by_shape

 **Full name**: None

 **Internal name**: mechanical:meshscoping_filtered_by_shape

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical:meshscoping_filtered_by_shape"); // operator instantiation
op.connect(0, my_requested_location);
op.connect(1, my_property_id);
op.connect(7, my_mesh);
ansys::dpf::Scoping my_mesh_scoping = op.getOutput<ansys::dpf::Scoping>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.mechanical_mesh_scoping_filtered_by_shape() # operator instantiation
op.inputs.requested_location.connect(my_requested_location)
op.inputs.property_id.connect(my_property_id)
op.inputs.mesh.connect(my_mesh)
my_mesh_scoping = op.outputs.mesh_scoping()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.mechanical_mesh_scoping_filtered_by_shape() # operator instantiation
op.inputs.requested_location.Connect(my_requested_location)
op.inputs.property_id.Connect(my_property_id)
op.inputs.mesh.Connect(my_mesh)
my_mesh_scoping = op.outputs.mesh_scoping.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.