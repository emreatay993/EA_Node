---
category: metadata
plugin: core
license: None
---

# metadata:mesh_partitions_provider

**Version: 0.0.0**

## Description

Provide the element scoping for each partition of the mesh.

## Supported file types

This operator supports the following keys ([file formats](../../index.md#overview-of-dpf)) for each listed namespace (plugin/solver):

- cff: cas, flprj 

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) |  |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) |  |
| <strong>Pin 6</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  n_partitions |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Number of partitions |
| <strong>Pin 25</strong>|  region_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping), [`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | region id (integer) or vector of region ids (vector) or region scoping (scoping) of the model (region corresponds to zone for Fluid results or part for LSDyna results). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| scopings_container |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mesh_partitions_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mesh_partitions_provider"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(6, my_n_partitions);
op.connect(25, my_region_scoping);
ansys::dpf::ScopingsContainer my_scopings_container = op.getOutput<ansys::dpf::ScopingsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.n_partitions.connect(my_n_partitions)
op.inputs.region_scoping.connect(my_region_scoping)
my_scopings_container = op.outputs.scopings_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.n_partitions.Connect(my_n_partitions)
op.inputs.region_scoping.Connect(my_region_scoping)
my_scopings_container = op.outputs.scopings_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.