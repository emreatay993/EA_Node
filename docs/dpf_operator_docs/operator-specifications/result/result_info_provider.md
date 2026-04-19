---
category: result
plugin: mapdl
license: None
---

# result:result info provider

**Version: 0.0.0**

## Description

Read result info from the rst file.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) |  |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) |  |
| <strong>Pin 200</strong>|  laziness |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) | configurate whether lazy evaluation can be performed and to what extent. Supported attributes are: <br>- int attribute 'ReadResultsAtCentroidInfo' with 0 (won't read) or 1 (will read).<br>- bool (optional) with 0 if you want the full ResultInfo or 1 if you only need to know the location from ResultInfo. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| result_info |[`result_info`](../../core-concepts/dpf-types.md#result-info) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: result_info_provider

 **Full name**: result.result_info_provider

 **Internal name**: mapdl::rstp::ResultInfoProvider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rstp::ResultInfoProvider"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(200, my_laziness);
ansys::dpf::ResultInfo my_result_info = op.getOutput<ansys::dpf::ResultInfo>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.result_info_provider() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.laziness.connect(my_laziness)
my_result_info = op.outputs.result_info()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.result_info_provider() # operator instantiation
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.laziness.Connect(my_laziness)
my_result_info = op.outputs.result_info.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.