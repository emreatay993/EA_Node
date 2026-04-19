---
category: result
plugin: mapdl
license: None
---

# result:mapdl::filter_meshes

**Version: 0.0.0**

## Description

Filter MAPDL meshes degenerated elements.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  meshes_container |[`meshes_container`](../../core-concepts/dpf-types.md#meshes-container) |  |
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container), `stream` |  |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| meshes_container |[`meshes_container`](../../core-concepts/dpf-types.md#meshes-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::filter_meshes

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::filter_meshes"); // operator instantiation
op.connect(0, my_meshes_container);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
ansys::dpf::MeshesContainer my_meshes_container = op.getOutput<ansys::dpf::MeshesContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.meshes_container.connect(my_meshes_container)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
my_meshes_container = op.outputs.meshes_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.meshes_container.Connect(my_meshes_container)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
my_meshes_container = op.outputs.meshes_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.