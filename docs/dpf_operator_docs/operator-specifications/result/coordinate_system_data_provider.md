---
category: result
plugin: mapdl
license: None
---

# result:coordinate system data provider

**Version: 0.0.0**

## Description

Reads coordinate systems data from the result files contained in the streams or data sources.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 1</strong>|  solver_coordinate_system_ids |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | Coordinate System ids to recover used by the solver. If not set, all available coordinate systems to be recovered. |
| <strong>Pin 3</strong>|  streams |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | Result file container allowed to be kept open to cache data. |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | Result file path container, used if no streams are set. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| coordinate_system_data |[`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) | The rotation matrix field stores the transformation matrix from local to global coordinate system. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: coordinate_system_data_provider

 **Full name**: result.coordinate_system_data_provider

 **Internal name**: mapdl::rstp::coordinate_systems_data_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rstp::coordinate_systems_data_provider"); // operator instantiation
op.connect(1, my_solver_coordinate_system_ids);
op.connect(3, my_streams);
op.connect(4, my_data_sources);
ansys::dpf::GenericDataContainer my_coordinate_system_data = op.getOutput<ansys::dpf::GenericDataContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.coordinate_system_data_provider() # operator instantiation
op.inputs.solver_coordinate_system_ids.connect(my_solver_coordinate_system_ids)
op.inputs.streams.connect(my_streams)
op.inputs.data_sources.connect(my_data_sources)
my_coordinate_system_data = op.outputs.coordinate_system_data()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.coordinate_system_data_provider() # operator instantiation
op.inputs.solver_coordinate_system_ids.Connect(my_solver_coordinate_system_ids)
op.inputs.streams.Connect(my_streams)
op.inputs.data_sources.Connect(my_data_sources)
my_coordinate_system_data = op.outputs.coordinate_system_data.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.