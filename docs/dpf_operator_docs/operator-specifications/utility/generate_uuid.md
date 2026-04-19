---
category: utility
plugin: core
license: None
---

# utility:generate uuid

**Version: 0.0.0**

## Description

Generates a uuid.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin -1**| raw_uuid | | boost::uuids::uuid |
|  **Pin 0**| uuid |[`string`](../../core-concepts/dpf-types.md#standard-types) | stringified uuid returned as 36 bytes string. |
|  **Pin 1**| bytes_uuid |[`string`](../../core-concepts/dpf-types.md#standard-types) | uuid returned as 16 bytes string. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: generate_uuid

 **Full name**: utility.generate_uuid

 **Internal name**: generate_uuid

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("generate_uuid"); // operator instantiation
 my_raw_uuid = op.getOutput<>(-1);
std::string my_uuid = op.getOutput<std::string>(0);
std::string my_bytes_uuid = op.getOutput<std::string>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.generate_uuid() # operator instantiation
my_raw_uuid = op.outputs.raw_uuid()
my_uuid = op.outputs.uuid()
my_bytes_uuid = op.outputs.bytes_uuid()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.generate_uuid() # operator instantiation
my_raw_uuid = op.outputs.raw_uuid.GetData()
my_uuid = op.outputs.uuid.GetData()
my_bytes_uuid = op.outputs.bytes_uuid.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.