---
category: result
plugin: mapdl
license: None
---

# result:mode data

**Version: 0.0.0**

## Description

Read mode types (standard, residual vectors, enformed motion modes) from mode file and return the number of modes of each type.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | Streams Container (must contain at least one mode file). |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | Data_sources (must contain at least one mode file). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| mode_types_number |[`scoping`](../../core-concepts/dpf-types.md#scoping) | Scoping holding mode number by type. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::mode::mode_data

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::mode::mode_data"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
ansys::dpf::Scoping my_mode_types_number = op.getOutput<ansys::dpf::Scoping>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
my_mode_types_number = op.outputs.mode_types_number()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
my_mode_types_number = op.outputs.mode_types_number.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.