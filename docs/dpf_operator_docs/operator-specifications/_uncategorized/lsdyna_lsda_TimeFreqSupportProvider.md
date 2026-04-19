---
category: None
plugin: N/A
license: None
---

# lsdyna::lsda::TimeFreqSupportProvider

**Version: 0.0.0**

## Description

Reads the TimeFreqSupport from a lsda file, assuming the file format from the lsdyna::lsda::export operator.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | lsda data sources |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) | time freq support |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: lsdyna::lsda::TimeFreqSupportProvider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("lsdyna::lsda::TimeFreqSupportProvider"); // operator instantiation
op.connect(4, my_data_sources);
ansys::dpf::TimeFreqSupport my_time_freq_support = op.getOutput<ansys::dpf::TimeFreqSupport>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.data_sources.connect(my_data_sources)
my_time_freq_support = op.outputs.time_freq_support()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.data_sources.Connect(my_data_sources)
my_time_freq_support = op.outputs.time_freq_support.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.