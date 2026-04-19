---
category: result
plugin: mapdl
license: None
---

# result:stream provider

**Version: 0.0.0**

## Description

Create mapdl streams based on a given data sources.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 200</strong>|  laziness |[`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) | configurate whether lazy evaluation can be performed and to what extent. Supported attributes are: <br>- int attribute 'ReadLevel' related to the rst level we want to read from 1 to 3 (default 1).<br>- int attribute 'BufferSize' is the size of the memory buffer used to read the rst file (default 256Mo).<br>- int attribute 'ReadMethod'. Method used to read the rst file with 1 (default) corresponding to buffer (read and write) and 2 corresponding to memory map.<br>- double attribute 'OverrideMinimumVersion'. Override the minimum version allowed when opening result files.<br> |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| stream_provider |`class dataProcessing::mapdl::CStreamProvider` |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: stream_provider

 **Full name**: result.stream_provider

 **Internal name**: mapdl::stream_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::stream_provider"); // operator instantiation
op.connect(200, my_laziness);
ansys::dpf::Class Dataprocessing::Mapdl::Cstreamprovider my_stream_provider = op.getOutput<ansys::dpf::Class Dataprocessing::Mapdl::Cstreamprovider>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.stream_provider() # operator instantiation
op.inputs.laziness.connect(my_laziness)
my_stream_provider = op.outputs.stream_provider()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.stream_provider() # operator instantiation
op.inputs.laziness.Connect(my_laziness)
my_stream_provider = op.outputs.stream_provider.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.