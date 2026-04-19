---
category: utility
plugin: core
license: None
---

# utility:mechanical: morphing evaluation frequency

**Version: 0.0.0**

## Description

Get evaluation frequency for Morphing Region object.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  current_frequency_field |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 1</strong>|  previous_frequency_field |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 2</strong>|  other_frequencies_field |[`field`](../../core-concepts/dpf-types.md#field) | minimum, maximum, minimum of analysis settings and maximum of analysis settings frequencies |
| <strong>Pin 3</strong>|  intervals |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0:morph at all frequencies' or x:number of frequency intervals', default 0 |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| evaluation_frequency |[`field`](../../core-concepts/dpf-types.md#field) |  |
|  **Pin 1**| morphing_required |[`bool`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mechanical::morphing_evaluation_frequency

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical::morphing_evaluation_frequency"); // operator instantiation
op.connect(0, my_current_frequency_field);
op.connect(1, my_previous_frequency_field);
op.connect(2, my_other_frequencies_field);
op.connect(3, my_intervals);
ansys::dpf::Field my_evaluation_frequency = op.getOutput<ansys::dpf::Field>(0);
bool my_morphing_required = op.getOutput<bool>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.current_frequency_field.connect(my_current_frequency_field)
op.inputs.previous_frequency_field.connect(my_previous_frequency_field)
op.inputs.other_frequencies_field.connect(my_other_frequencies_field)
op.inputs.intervals.connect(my_intervals)
my_evaluation_frequency = op.outputs.evaluation_frequency()
my_morphing_required = op.outputs.morphing_required()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.current_frequency_field.Connect(my_current_frequency_field)
op.inputs.previous_frequency_field.Connect(my_previous_frequency_field)
op.inputs.other_frequencies_field.Connect(my_other_frequencies_field)
op.inputs.intervals.Connect(my_intervals)
my_evaluation_frequency = op.outputs.evaluation_frequency.GetData()
my_morphing_required = op.outputs.morphing_required.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.