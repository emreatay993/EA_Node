---
category: utility
plugin: core
license: None
---

# utility:mechanical: rescope time freq support

**Version: 0.0.0**

## Description

Rescopes TimeFreqSupport for a given load step.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  load_step |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | Load step to rescope the TimeFreqSupport data |
| <strong>Pin 8</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mechanical::rescope_time_freq_support

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical::rescope_time_freq_support"); // operator instantiation
op.connect(1, my_load_step);
op.connect(8, my_time_freq_support);
ansys::dpf::TimeFreqSupport my_time_freq_support = op.getOutput<ansys::dpf::TimeFreqSupport>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.load_step.connect(my_load_step)
op.inputs.time_freq_support.connect(my_time_freq_support)
my_time_freq_support = op.outputs.time_freq_support()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.load_step.Connect(my_load_step)
op.inputs.time_freq_support.Connect(my_time_freq_support)
my_time_freq_support = op.outputs.time_freq_support.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.