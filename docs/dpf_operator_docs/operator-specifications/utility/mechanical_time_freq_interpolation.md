---
category: utility
plugin: core
license: None
---

# utility:mechanical: time freq interpolation

**Version: 0.0.0**

## Description

Interpolates results of time or frequencies depending on Mechanical options.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  target_time_freq_values |[`field`](../../core-concepts/dpf-types.md#field), [`vector<double>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  analysis_time_freq_values |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 3</strong>|  interpolation_type |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 1:ramped' or 2:stepped', default is ramped |
| <strong>Pin 4</strong>|  initial_values |[`double`](../../core-concepts/dpf-types.md#standard-types), [`field`](../../core-concepts/dpf-types.md#field), [`vector<double>`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 5</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  source_time_freq_values |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 6</strong>|  entire_source_time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) | TimeFreqSupport of the source time freqs with all the the source time/freqs: if source_time_freq_values is a chunk, entire_source_time_freq_support is not chunked |
| <strong>Pin 7</strong>|  entire_target_time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) | TimeFreqSupport of the target time freqs with all the the source time/freqs: if target_time_freq_values is a chunk, entire_target_time_freq_support is not chunked |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |
|  **Pin 1**| time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mechanical::time_freq_interpolation

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical::time_freq_interpolation"); // operator instantiation
op.connect(0, my_fields_container);
op.connect(1, my_target_time_freq_values);
op.connect(2, my_analysis_time_freq_values);
op.connect(3, my_interpolation_type);
op.connect(4, my_initial_values);
op.connect(5, my_source_time_freq_values);
op.connect(6, my_entire_source_time_freq_support);
op.connect(7, my_entire_target_time_freq_support);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
ansys::dpf::TimeFreqSupport my_time_freq_support = op.getOutput<ansys::dpf::TimeFreqSupport>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.fields_container.connect(my_fields_container)
op.inputs.target_time_freq_values.connect(my_target_time_freq_values)
op.inputs.analysis_time_freq_values.connect(my_analysis_time_freq_values)
op.inputs.interpolation_type.connect(my_interpolation_type)
op.inputs.initial_values.connect(my_initial_values)
op.inputs.source_time_freq_values.connect(my_source_time_freq_values)
op.inputs.entire_source_time_freq_support.connect(my_entire_source_time_freq_support)
op.inputs.entire_target_time_freq_support.connect(my_entire_target_time_freq_support)
my_fields_container = op.outputs.fields_container()
my_time_freq_support = op.outputs.time_freq_support()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.fields_container.Connect(my_fields_container)
op.inputs.target_time_freq_values.Connect(my_target_time_freq_values)
op.inputs.analysis_time_freq_values.Connect(my_analysis_time_freq_values)
op.inputs.interpolation_type.Connect(my_interpolation_type)
op.inputs.initial_values.Connect(my_initial_values)
op.inputs.source_time_freq_values.Connect(my_source_time_freq_values)
op.inputs.entire_source_time_freq_support.Connect(my_entire_source_time_freq_support)
op.inputs.entire_target_time_freq_support.Connect(my_entire_target_time_freq_support)
my_fields_container = op.outputs.fields_container.GetData()
my_time_freq_support = op.outputs.time_freq_support.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.