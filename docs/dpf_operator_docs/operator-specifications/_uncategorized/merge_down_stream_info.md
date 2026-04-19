---
category: None
plugin: core
license: None
---

# merge::down_stream_info

**Version: 0.0.0**

## Description

Assembles a set of downstream information into a unique one.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  downstream_information |[`vector<shared_ptr<down_stream_info>>`](../../core-concepts/dpf-types.md#vector<shared-ptr<down-stream-info>>) | A vector of downstream information to merge |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| merged_downstream_information |[`down_stream_info`](../../core-concepts/dpf-types.md#down-stream-info) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: merge::down_stream_info

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("merge::down_stream_info"); // operator instantiation
op.connect(0, my_downstream_information);
ansys::dpf::DownStreamInfo my_merged_downstream_information = op.getOutput<ansys::dpf::DownStreamInfo>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.downstream_information.connect(my_downstream_information)
my_merged_downstream_information = op.outputs.merged_downstream_information()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.downstream_information.Connect(my_downstream_information)
my_merged_downstream_information = op.outputs.merged_downstream_information.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.