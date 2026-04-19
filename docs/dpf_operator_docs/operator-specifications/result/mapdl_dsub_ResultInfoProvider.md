---
category: result
plugin: mapdl
license: None
---

# result:mapdl::dsub::ResultInfoProvider

**Version: 0.0.0**

## Description

Read from a use pass file in a recursive manner.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | streams (result file container) (optional) |
| <strong>Pin 4</strong>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | dataSources // if stream is null then we need to get the file path from the data sources |
| <strong>Pin 200</strong>|  bool |[`bool`](../../core-concepts/dpf-types.md#standard-types) | use_upstreams bolean (default = true) |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| any |[`any`](../../core-concepts/dpf-types.md#any) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **permissive** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, warning checks (like unit or data sizes) won't be done. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::dsub::ResultInfoProvider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::dsub::ResultInfoProvider"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(200, my_bool);
ansys::dpf::Any my_any = op.getOutput<ansys::dpf::Any>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.bool.connect(my_bool)
my_any = op.outputs.any()
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
op.inputs.bool.Connect(my_bool)
my_any = op.outputs.any.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.