---
category: None
plugin: N/A
license: None
---

# lsdyna::lsda::export

**Version: 0.0.0**

## Description

Writes loads from fields container in lsda format.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  ansys_unit_system_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | defines the UnitSystem the results are exported with. Default: 11 (solver_mks). |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | the output file path |
| <strong>Pin 5</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | input results field container |
| <strong>Pin 6</strong>|  frequency_threshold |[`double`](../../core-concepts/dpf-types.md#standard-types) | removes all frequencies strictly lower than the input value. 0.0 by default. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: lsdyna::lsda::export

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lsdyna::lsda::export"); // operator instantiation
op.connect(3, my_ansys_unit_system_id);
op.connect(4, my_data_sources);
op.connect(5, my_fields_container);
op.connect(6, my_frequency_threshold);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.ansys_unit_system_id.connect(my_ansys_unit_system_id)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.fields_container.connect(my_fields_container)
op.inputs.frequency_threshold.connect(my_frequency_threshold)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.ansys_unit_system_id.Connect(my_ansys_unit_system_id)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.fields_container.Connect(my_fields_container)
op.inputs.frequency_threshold.Connect(my_frequency_threshold)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.