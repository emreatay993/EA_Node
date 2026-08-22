---
category: None
plugin: core
license: any_dpf_supported_increments
---

# topology::moment_of_inertia

**Version: 0.0.0**

## Description

Compute the inertia tensor of a set of elements.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  topology |[`abstract_topology_entity`](../../core-concepts/dpf-types.md#topology-entity) |  |
| <strong>Pin 1</strong>|  mesh_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) | Mesh scoping, if not set, all the elements of the mesh are considered. |
| <strong>Pin 2</strong>|  field |[`field`](../../core-concepts/dpf-types.md#field) | Elemental or nodal ponderation used in computation. |
| <strong>Pin 3</strong>|  boolean |[`bool`](../../core-concepts/dpf-types.md#standard-types) | default true, compute inertia tensor at center of gravity. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| field |[`field`](../../core-concepts/dpf-types.md#field) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: topology::moment_of_inertia

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("topology::moment_of_inertia"); // operator instantiation
op.connect(0, my_topology);
op.connect(1, my_mesh_scoping);
op.connect(2, my_field);
op.connect(3, my_boolean);
ansys::dpf::Field my_field = op.getOutput<ansys::dpf::Field>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.topology.connect(my_topology)
op.inputs.mesh_scoping.connect(my_mesh_scoping)
op.inputs.field.connect(my_field)
op.inputs.boolean.connect(my_boolean)
my_field = op.outputs.field()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.topology.Connect(my_topology)
op.inputs.mesh_scoping.Connect(my_mesh_scoping)
op.inputs.field.Connect(my_field)
op.inputs.boolean.Connect(my_boolean)
my_field = op.outputs.field.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.