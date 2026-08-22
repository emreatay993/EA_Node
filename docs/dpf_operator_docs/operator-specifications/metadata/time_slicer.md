---
category: metadata
plugin: core
license: None
---

# metadata:time slicer

**Version: 0.0.0**

## Description

Create multiple slices of a Time scoped Field having a TimeFreqSupport.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  slice_number |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Number of slices. |
| <strong>Pin 2</strong>|  overlap |[`double`](../../core-concepts/dpf-types.md#standard-types) | Slices overlap (default is 0%). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) | TimeFreqSupport having each load step representing a slice, central slice time set as RPM. |
|  **Pin 1**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | FieldsContainer having slice label, central slice time set as RPM. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: time_slicer

 **Full name**: metadata.time_slicer

 **Internal name**: timefreq::timeslicer

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("timefreq::timeslicer"); // operator instantiation
op.connect(0, my_field);
op.connect(1, my_slice_number);
op.connect(2, my_overlap);
ansys::dpf::TimeFreqSupport my_time_freq_support = op.getOutput<ansys::dpf::TimeFreqSupport>(0);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.time_slicer() # operator instantiation
op.inputs.field.connect(my_field)
op.inputs.slice_number.connect(my_slice_number)
op.inputs.overlap.connect(my_overlap)
my_time_freq_support = op.outputs.time_freq_support()
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.time_slicer() # operator instantiation
op.inputs.field.Connect(my_field)
op.inputs.slice_number.Connect(my_slice_number)
op.inputs.overlap.Connect(my_overlap)
my_time_freq_support = op.outputs.time_freq_support.GetData()
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.