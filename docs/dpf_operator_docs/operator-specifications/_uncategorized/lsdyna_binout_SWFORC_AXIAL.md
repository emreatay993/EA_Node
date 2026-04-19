---
category: None
plugin: N/A
license: None
---

# lsdyna::binout::SWFORC_AXIAL

**Version: 0.0.0**

## Description

Read swforc axial from result streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | streams (result file container) (optional) |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | if the stream is null then we need to get the file path from the data sources |
| <strong>Pin 50</strong>|  unit_system |[`UnitSystem`](../../core-concepts/dpf-types.md#unitsystem) | UnitSystem |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| swforc_axial |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | swforc_axial |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: lsdyna::binout::SWFORC_AXIAL

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lsdyna::binout::SWFORC_AXIAL"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(50, my_unit_system);
ansys::dpf::FieldsContainer my_swforc_axial = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.unit_system.connect(my_unit_system)
my_swforc_axial = op.outputs.swforc_axial()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.unit_system.Connect(my_unit_system)
my_swforc_axial = op.outputs.swforc_axial.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.