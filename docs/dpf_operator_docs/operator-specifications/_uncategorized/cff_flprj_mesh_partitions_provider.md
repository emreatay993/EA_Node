---
category: None
plugin: N/A
license: None
---

# cff::flprj::mesh_partitions_provider

**Version: 0.0.0**

## Description

Partitions the mesh domain to prepare distributed postprocessing.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  time_scoping |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`scoping`](../../core-concepts/dpf-types.md#scoping) | time id (integer) or vector with a single time id (vector) required in output |
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | result file container allowed to be kept open to cache data |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | result file path container |
| <strong>Pin 6</strong>|  num_partitions |[`int32`](../../core-concepts/dpf-types.md#standard-types) | number of partitions. if partitions are available in the file, the partitions in the file take precedence |
| <strong>Pin 25</strong>|  zone_id |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`scoping`](../../core-concepts/dpf-types.md#scoping) | zone id (integer) or vector with a single zone id (vector) or scoping with a single zone id (scoping) |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| scopings_container |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | partition scopings container |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cff::flprj::mesh_partitions_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cff::flprj::mesh_partitions_provider"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(6, my_num_partitions);
op.connect(25, my_zone_id);
ansys::dpf::ScopingsContainer my_scopings_container = op.getOutput<ansys::dpf::ScopingsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.num_partitions.connect(my_num_partitions)
op.inputs.zone_id.connect(my_zone_id)
my_scopings_container = op.outputs.scopings_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.num_partitions.Connect(my_num_partitions)
op.inputs.zone_id.Connect(my_zone_id)
my_scopings_container = op.outputs.scopings_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.