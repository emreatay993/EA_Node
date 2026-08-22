---
category: math
plugin: core
license: None
---

# math:stft (fields container)

**Version: 0.0.0**

## Description

Perform Short Term Fourier Transform on a time scoped field having a TimeFreqSupport.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  cutoff_frequency |[`double`](../../core-concepts/dpf-types.md#standard-types) | max frequency in output |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  min_freq_resolution |[`double`](../../core-concepts/dpf-types.md#standard-types) | minimum frequency resolution (difference between each frequency in output) |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  slice_number |[`int32`](../../core-concepts/dpf-types.md#standard-types) | number of stft slices |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  overlap |[`double`](../../core-concepts/dpf-types.md#standard-types) | overlapping of between slices |
| <strong>Pin 5</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  window |[`int32`](../../core-concepts/dpf-types.md#standard-types) | connect max number subdivisions, used to avoid huge number of sudivisions |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields Container having Slice label, each field representing a fft on slice. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: math

 **Plugin**: core

 **Scripting name**: stft_fc

 **Full name**: math.stft_fc

 **Internal name**: stft_fc

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("stft_fc"); // operator instantiation
op.connect(0, my_fields_container);
op.connect(1, my_cutoff_frequency);
op.connect(2, my_min_freq_resolution);
op.connect(3, my_slice_number);
op.connect(4, my_overlap);
op.connect(5, my_window);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.math.stft_fc() # operator instantiation
op.inputs.fields_container.connect(my_fields_container)
op.inputs.cutoff_frequency.connect(my_cutoff_frequency)
op.inputs.min_freq_resolution.connect(my_min_freq_resolution)
op.inputs.slice_number.connect(my_slice_number)
op.inputs.overlap.connect(my_overlap)
op.inputs.window.connect(my_window)
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.math.stft_fc() # operator instantiation
op.inputs.fields_container.Connect(my_fields_container)
op.inputs.cutoff_frequency.Connect(my_cutoff_frequency)
op.inputs.min_freq_resolution.Connect(my_min_freq_resolution)
op.inputs.slice_number.Connect(my_slice_number)
op.inputs.overlap.Connect(my_overlap)
op.inputs.window.Connect(my_window)
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.