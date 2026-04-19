---
category: metadata
plugin: core
license: None
---

# metadata:remote operator release

**Version: 0.0.0**

## Description

Release a remote operator for a given protocol registered in the streams.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 1</strong>|  streams_holder_wwf_remote_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Id a workflow holding the grpc stream in the server database. The workflow with this id is deleted if this input is set. |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  remote_operator |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: remote_operator_release

 **Full name**: metadata.remote_operator_release

 **Internal name**: remote_operator_release

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("remote_operator_release"); // operator instantiation
op.connect(0, my_remote_id);
op.connect(1, my_streams_holder_wwf_remote_id);
op.connect(3, my_remote_operator);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.remote_operator_release() # operator instantiation
op.inputs.remote_id.connect(my_remote_id)
op.inputs.streams_holder_wwf_remote_id.connect(my_streams_holder_wwf_remote_id)
op.inputs.remote_operator.connect(my_remote_operator)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.remote_operator_release() # operator instantiation
op.inputs.remote_id.Connect(my_remote_id)
op.inputs.streams_holder_wwf_remote_id.Connect(my_streams_holder_wwf_remote_id)
op.inputs.remote_operator.Connect(my_remote_operator)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.