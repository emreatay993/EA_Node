---
category: utility
plugin: core
license: None
---

# utility:license status

**Version: 0.0.0**

## Description

Returns currently checked out license increments as a comma separated list.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| status |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: license_status

 **Full name**: utility.license_status

 **Internal name**: license_status

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("license_status"); // operator instantiation
std::string my_status = op.getOutput<std::string>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.license_status() # operator instantiation
my_status = op.outputs.status()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.license_status() # operator instantiation
my_status = op.outputs.status.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.