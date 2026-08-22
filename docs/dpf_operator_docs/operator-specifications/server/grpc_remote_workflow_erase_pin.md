---
category: server
plugin: grpc
license: None
---

# server:grpc::remote_workflow_erase_pin

**Version: 0.0.0**

## Description



## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: server

 **Plugin**: grpc

 **Scripting name**: None

 **Full name**: None

 **Internal name**: grpc::remote_workflow_erase_pin

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("grpc::remote_workflow_erase_pin"); // operator instantiation
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.server.None() # operator instantiation
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.server.None() # operator instantiation
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.