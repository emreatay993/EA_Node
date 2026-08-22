---
category: None
plugin: N/A
license: None
---

# cff::data_sources_provider

**Version: 0.0.0**

## Description

Complete data sources if a an flprj file is used.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | result file path container |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 4**| data_sources |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | result file path container with added files. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cff::data_sources_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cff::data_sources_provider"); // operator instantiation
op.connect(4, my_data_sources);
ansys::dpf::Streams my_data_sources = op.getOutput<ansys::dpf::Streams>(4);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.data_sources.connect(my_data_sources)
my_data_sources = op.outputs.data_sources()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.data_sources.Connect(my_data_sources)
my_data_sources = op.outputs.data_sources.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.