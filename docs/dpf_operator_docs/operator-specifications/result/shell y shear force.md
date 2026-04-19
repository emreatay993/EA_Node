---
category: result
plugin: N/A
license: None
---

# result:lsdyna::d3plot::qy

**Version: 0.0.0**

## Description

Read Shell Y Shear Force from result streams

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  time_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | time/freq (use doubles or field), time/freq set ids (use ints or scoping) or time/freq step ids (use scoping with TimeFreq_steps location) required in output |
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | streams (result file container) (optional) |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | if the stream is null then we need to get the file path from the data sources |
| <strong>Pin 25</strong>|  part_id |[`scoping`](../../core-concepts/dpf-types.md#scoping) | PartId |
| <strong>Pin 50</strong>|  unit_system |[`UnitSystem`](../../core-concepts/dpf-types.md#unitsystem) | UnitSystem |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| shell_y_shear_force |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | shell y shear force |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: N/A

 **Scripting name**: shell y shear force

 **Full name**: result.shell y shear force

 **Internal name**: lsdyna::d3plot::qy

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lsdyna::d3plot::qy"); // operator instantiation
op.connect(0, my_time_scoping);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(25, my_part_id);
op.connect(50, my_unit_system);
ansys::dpf::FieldsContainer my_shell_y_shear_force = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.shell y shear force() # operator instantiation
op.inputs.time_scoping.connect(my_time_scoping)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.part_id.connect(my_part_id)
op.inputs.unit_system.connect(my_unit_system)
my_shell_y_shear_force = op.outputs.shell_y_shear_force()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.shell y shear force() # operator instantiation
op.inputs.time_scoping.Connect(my_time_scoping)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.part_id.Connect(my_part_id)
op.inputs.unit_system.Connect(my_unit_system)
my_shell_y_shear_force = op.outputs.shell_y_shear_force.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.