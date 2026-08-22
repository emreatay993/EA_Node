---
category: utility
plugin: core
license: None
---

# utility:license check

**Version: 0.0.0**

## Description

Checks if specified increment_name is available. Does not checkout the license.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  increment_name |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 1</strong>|  time_out_in_seconds |[`double`](../../core-concepts/dpf-types.md#standard-types) | defaults to the global license_timeout_in_seconds config. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: license_check

 **Full name**: utility.license_check

 **Internal name**: license_check

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("license_check"); // operator instantiation
op.connect(0, my_increment_name);
op.connect(1, my_time_out_in_seconds);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.license_check() # operator instantiation
op.inputs.increment_name.connect(my_increment_name)
op.inputs.time_out_in_seconds.connect(my_time_out_in_seconds)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.license_check() # operator instantiation
op.inputs.increment_name.Connect(my_increment_name)
op.inputs.time_out_in_seconds.Connect(my_time_out_in_seconds)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.