---
category: utility
plugin: core
license: None
---

# utility:mechanical: create time freq support

**Version: 0.0.0**

## Description

Creates a TimeFreqSupport by copying the input one (if the input one has imaginary freqs, rpms, the output one will too) with new time freq values.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  time_freq_values |[`double`](../../core-concepts/dpf-types.md#standard-types), [`vector<double>`](../../core-concepts/dpf-types.md#standard-types), [`field`](../../core-concepts/dpf-types.md#field) | list of frequencies or times needed in the output TiemFreqSupport. To specify load steps, put a Field (and not a list) in input with a scoping located on "TimeFreq_steps" or a step in pin 2. |
| <strong>Pin 2</strong>|  step |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
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

 **Internal name**: mechanical::custom_create_time_freq_support

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical::custom_create_time_freq_support"); // operator instantiation
op.connect(0, my_time_freq_values);
op.connect(2, my_step);
op.connect(8, my_time_freq_support);
ansys::dpf::TimeFreqSupport my_time_freq_support = op.getOutput<ansys::dpf::TimeFreqSupport>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.time_freq_values.connect(my_time_freq_values)
op.inputs.step.connect(my_step)
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
op.inputs.time_freq_values.Connect(my_time_freq_values)
op.inputs.step.Connect(my_step)
op.inputs.time_freq_support.Connect(my_time_freq_support)
my_time_freq_support = op.outputs.time_freq_support.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.