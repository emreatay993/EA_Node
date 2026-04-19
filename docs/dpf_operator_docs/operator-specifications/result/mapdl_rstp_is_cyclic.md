---
category: result
plugin: mapdl
license: None
---

# result:mapdl::rstp::is_cyclic

**Version: 0.0.0**

## Description

Read if the model is cyclic form the rst file.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container), `stream` | Streams containing the result file. |
| <strong>Pin 4</strong>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | data sources containing the result file. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| file_path |[`string`](../../core-concepts/dpf-types.md#standard-types) | returns 'single_stage' or 'multi_stage' or an empty string |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::rstp::is_cyclic

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rstp::is_cyclic"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
std::string my_file_path = op.getOutput<std::string>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
my_file_path = op.outputs.file_path()
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
my_file_path = op.outputs.file_path.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.