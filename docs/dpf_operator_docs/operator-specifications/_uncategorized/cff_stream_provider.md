---
category: None
plugin: N/A
license: None
---

# cff::stream_provider

**Version: 0.0.0**

## Description

Creates streams (files with cache) from the data sources.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | result file path container |
| <strong>Pin 24</strong>|  analysis_type |[`int32`](../../core-concepts/dpf-types.md#standard-types) | analysis type according to the analysis_type enum |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | streams |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cff::stream_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cff::stream_provider"); // operator instantiation
op.connect(4, my_data_sources);
op.connect(24, my_analysis_type);
ansys::dpf::Streams my_streams_container = op.getOutput<ansys::dpf::Streams>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.data_sources.connect(my_data_sources)
op.inputs.analysis_type.connect(my_analysis_type)
my_streams_container = op.outputs.streams_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.analysis_type.Connect(my_analysis_type)
my_streams_container = op.outputs.streams_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.