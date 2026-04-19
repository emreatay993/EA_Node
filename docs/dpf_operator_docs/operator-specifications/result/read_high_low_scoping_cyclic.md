---
category: result
plugin: mapdl
license: None
---

# result:read_high_low_scoping_cyclic

**Version: 0.0.0**

## Description

Read maps of nodes ids for high and low boundaries for cyclic analysis from a txt or dat file (one for each stage)

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | data_sources with a txt or dat file containing a map of nodes id for high and low boundaries for cyclic analysis |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| high_low_nodes_map_vector |[`vector<shared_ptr<low_high_scoping_map>>`](../../core-concepts/dpf-types.md#vector<shared-ptr<low-high-scoping-map>>) | vector CLowHighScopingMap of node ids for high and low cyclic boundaries (one for each stage)  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: read_high_low_scoping_cyclic

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("read_high_low_scoping_cyclic"); // operator instantiation
op.connect(4, my_data_sources);
std::vector<ansys::dpf::SharedPtr<LowHighScopingMap>> my_high_low_nodes_map_vector = op.getOutput<std::vector<ansys::dpf::SharedPtr<LowHighScopingMap>>>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.data_sources.connect(my_data_sources)
my_high_low_nodes_map_vector = op.outputs.high_low_nodes_map_vector()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.data_sources.Connect(my_data_sources)
my_high_low_nodes_map_vector = op.outputs.high_low_nodes_map_vector.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.