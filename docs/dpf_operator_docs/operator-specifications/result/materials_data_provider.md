---
category: result
plugin: mapdl
license: None
---

# result:materials data provider

**Version: 0.0.0**

## Description

Reads materials data from the result files contained in the streams or data sources.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  properties_names |[`string`](../../core-concepts/dpf-types.md#standard-types), [`vector<string>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  solver_material_ids |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) |  |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| material_data |[`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: materials_data_provider

 **Full name**: result.materials_data_provider

 **Internal name**: mapdl::rstp::materials_data_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rstp::materials_data_provider"); // operator instantiation
op.connect(0, my_properties_names);
op.connect(1, my_solver_material_ids);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
ansys::dpf::GenericDataContainer my_material_data = op.getOutput<ansys::dpf::GenericDataContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.materials_data_provider() # operator instantiation
op.inputs.properties_names.connect(my_properties_names)
op.inputs.solver_material_ids.connect(my_solver_material_ids)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
my_material_data = op.outputs.material_data()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.materials_data_provider() # operator instantiation
op.inputs.properties_names.Connect(my_properties_names)
op.inputs.solver_material_ids.Connect(my_solver_material_ids)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
my_material_data = op.outputs.material_data.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.