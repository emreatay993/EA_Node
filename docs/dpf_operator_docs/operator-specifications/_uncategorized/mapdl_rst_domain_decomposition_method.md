---
category: None
plugin: mapdl
license: None
---

# mapdl domain decomposition method reader

**Version: 0.0.0**

## Description

Reads the DECOMPMTH from a rst file that was generated from a DMP run and forwards it as an integer

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | result file container allowed to be kept open to cache data |
| <strong>Pin 4</strong>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | result file path container, used if no streams are set |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| decompMth |[`int32`](../../core-concepts/dpf-types.md#standard-types) | >=0 for MESH decomposition, -1 for FREQ decomposition and -2 for CYCHI decomposition |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::rst::domain_decomposition_method

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rst::domain_decomposition_method"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
int my_decompMth = op.getOutput<int>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
my_decompMth = op.outputs.decompMth()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
my_decompMth = op.outputs.decompMth.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.