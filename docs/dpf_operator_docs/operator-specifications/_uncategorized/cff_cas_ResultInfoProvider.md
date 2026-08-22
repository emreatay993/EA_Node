---
category: None
plugin: N/A
license: None
---

# cff::cas::ResultInfoProvider

**Version: 0.0.0**

## Description

Read the result info from result streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | streams (result file container) (optional) |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | if the stream is null then we need to get the file path from the data sources |
| <strong>Pin 24</strong>|  analysis_type |[`int32`](../../core-concepts/dpf-types.md#standard-types) | analysis type according to the analysis_type enum |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| result_info |[`result_info`](../../core-concepts/dpf-types.md#result-info) | result_info |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cff::cas::ResultInfoProvider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cff::cas::ResultInfoProvider"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(24, my_analysis_type);
ansys::dpf::ResultInfo my_result_info = op.getOutput<ansys::dpf::ResultInfo>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.analysis_type.connect(my_analysis_type)
my_result_info = op.outputs.result_info()
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
op.inputs.analysis_type.Connect(my_analysis_type)
my_result_info = op.outputs.result_info.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.