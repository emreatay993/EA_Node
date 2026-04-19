---
category: None
plugin: core
license: None
---

# no_merge::composite::MeshProvider

**Version: 0.0.0**

## Description

Similar to the composite::mesh_provider but instead of merging the meshes, it returns a vector of meshes

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  vector<shared_ptr<streams_container>> |[`vector<shared_ptr<streams_container>>`](../../core-concepts/dpf-types.md#vector<shared-ptr<streams-container>>) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| meshes |`vector<shared_ptr<abstract_meshed_region>>` |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: no_merge::composite::MeshProvider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("no_merge::composite::MeshProvider"); // operator instantiation
op.connect(3, my_vector<shared_ptr<streams_container>>);
std::vector<ansys::dpf::SharedPtr<AbstractMeshedRegion>> my_meshes = op.getOutput<std::vector<ansys::dpf::SharedPtr<AbstractMeshedRegion>>>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.vector<shared_ptr<streams_container>>.connect(my_vector<shared_ptr<streams_container>>)
my_meshes = op.outputs.meshes()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.vector<shared_ptr<streams_container>>.Connect(my_vector<shared_ptr<streams_container>>)
my_meshes = op.outputs.meshes.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.