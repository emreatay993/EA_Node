---
category: utility
plugin: core
license: None
---

# utility:license checkout

**Version: 0.0.0**

## Description

Checks out the specified increment on run and releases it on destruction.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  increment_name |[`string`](../../core-concepts/dpf-types.md#standard-types), [`vector<string>`](../../core-concepts/dpf-types.md#standard-types) | vector of increments are only supported for delay checkout (pin 2), otherwise if vector of increment is set as an input and delay checkout is set to 0 then only the first increment is checked out |
| <strong>Pin 1</strong>|  time_out_in_seconds |[`double`](../../core-concepts/dpf-types.md#standard-types) | defaults to the global license_timeout_in_seconds config. |
| <strong>Pin 2</strong>|  delay_checkout |[`int32`](../../core-concepts/dpf-types.md#standard-types) | when this pin is set to 1, then all operators requiring any dpf license will checkout one of the specified licenses in pin 0 |

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

 **Scripting name**: license_checkout

 **Full name**: utility.license_checkout

 **Internal name**: license_checkout

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("license_checkout"); // operator instantiation
op.connect(0, my_increment_name);
op.connect(1, my_time_out_in_seconds);
op.connect(2, my_delay_checkout);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.license_checkout() # operator instantiation
op.inputs.increment_name.connect(my_increment_name)
op.inputs.time_out_in_seconds.connect(my_time_out_in_seconds)
op.inputs.delay_checkout.connect(my_delay_checkout)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.license_checkout() # operator instantiation
op.inputs.increment_name.Connect(my_increment_name)
op.inputs.time_out_in_seconds.Connect(my_time_out_in_seconds)
op.inputs.delay_checkout.Connect(my_delay_checkout)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.