---
category: math
plugin: core
license: None
---

# math:sampler

**Version: 0.0.0**

## Description

Linearly sample a field having a time freq support in input.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field |[`field`](../../core-concepts/dpf-types.md#field) | Time scoped field having a TimeFreqSupport |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  frequency |[`double`](../../core-concepts/dpf-types.md#standard-types) | Sampling frequency. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| field |[`field`](../../core-concepts/dpf-types.md#field) | Sampled field data at the specified frequency |
|  **Pin 1**| time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) | TimeFreqSupport for the sampled data |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: math

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: sampler

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("sampler"); // operator instantiation
op.connect(0, my_field);
op.connect(1, my_frequency);
ansys::dpf::Field my_field = op.getOutput<ansys::dpf::Field>(0);
ansys::dpf::TimeFreqSupport my_time_freq_support = op.getOutput<ansys::dpf::TimeFreqSupport>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.math.None() # operator instantiation
op.inputs.field.connect(my_field)
op.inputs.frequency.connect(my_frequency)
my_field = op.outputs.field()
my_time_freq_support = op.outputs.time_freq_support()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.math.None() # operator instantiation
op.inputs.field.Connect(my_field)
op.inputs.frequency.Connect(my_frequency)
my_field = op.outputs.field.GetData()
my_time_freq_support = op.outputs.time_freq_support.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.