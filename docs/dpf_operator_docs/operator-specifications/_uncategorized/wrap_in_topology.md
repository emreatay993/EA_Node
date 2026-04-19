---
category: None
plugin: core
license: any_dpf_supported_increments
---

# wrap in topology

**Version: 0.0.0**

## Description

Take various input, and wrap in geometry if necessary.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region), [`abstract_topology_entity`](../../core-concepts/dpf-types.md#topology-entity) |  |
| <strong>Pin 1</strong>|  id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Id that must be attributed to the generated geometry (default is 0). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| mesh |[`abstract_topology_entity`](../../core-concepts/dpf-types.md#topology-entity) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: wrap_in_topology

 **Full name**: None

 **Internal name**: topology::topology_from_mesh

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("topology::topology_from_mesh"); // operator instantiation
op.connect(0, my_mesh);
op.connect(1, my_id);
ansys::dpf::AbstractTopologyEntity my_mesh = op.getOutput<ansys::dpf::AbstractTopologyEntity>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.wrap_in_topology() # operator instantiation
op.inputs.mesh.connect(my_mesh)
op.inputs.id.connect(my_id)
my_mesh = op.outputs.mesh()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.wrap_in_topology() # operator instantiation
op.inputs.mesh.Connect(my_mesh)
op.inputs.id.Connect(my_id)
my_mesh = op.outputs.mesh.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.