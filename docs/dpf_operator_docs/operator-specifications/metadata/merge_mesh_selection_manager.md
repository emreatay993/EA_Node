---
category: metadata
plugin: core
license: None
---

# metadata:merge::mesh_selection_manager

**Version: 0.0.0**

## Description

Assembles a set of mesh selection managers into a unique one.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin -1</strong>|  merged_mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) | Already merged mesh. |
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mesh_selection_managers |[`vector<shared_ptr<mesh_selection_manager>>`](../../core-concepts/dpf-types.md#vector<shared-ptr<mesh-selection-manager>>), `mesh_selection_manager` | A vector of mesh selection managers to merge. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| merged_mesh_selection_manager |`mesh_selection_manager` |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: merge::mesh_selection_manager

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("merge::mesh_selection_manager"); // operator instantiation
op.connect(-1, my_merged_mesh);
op.connect(0, my_mesh_selection_managers);
ansys::dpf::MeshSelectionManager my_merged_mesh_selection_manager = op.getOutput<ansys::dpf::MeshSelectionManager>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.merged_mesh.connect(my_merged_mesh)
op.inputs.mesh_selection_managers.connect(my_mesh_selection_managers)
my_merged_mesh_selection_manager = op.outputs.merged_mesh_selection_manager()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.merged_mesh.Connect(my_merged_mesh)
op.inputs.mesh_selection_managers.Connect(my_mesh_selection_managers)
my_merged_mesh_selection_manager = op.outputs.merged_mesh_selection_manager.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.