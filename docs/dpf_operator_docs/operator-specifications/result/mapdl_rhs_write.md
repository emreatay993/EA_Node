---
category: result
plugin: mapdl
license: None
---

# result:mapdl::rhs::write

**Version: 0.0.0**

## Description

Write an mapdl right hand side file in the ANSYS flavour of harwell-boeing format

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  FileName |[`string`](../../core-concepts/dpf-types.md#standard-types) | File name of the output file, must be encoded in UTF-8. |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  RightHandSide |[`field`](../../core-concepts/dpf-types.md#field) | Right hand side values that must be written in the file. |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | Input streams (must contain one or more rst files). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| ProducedFile |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | DataSources filled with the generated RHS file. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::rhs::write

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rhs::write"); // operator instantiation
op.connect(0, my_FileName);
op.connect(1, my_RightHandSide);
op.connect(3, my_streams_container);
ansys::dpf::DataSources my_ProducedFile = op.getOutput<ansys::dpf::DataSources>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.FileName.connect(my_FileName)
op.inputs.RightHandSide.connect(my_RightHandSide)
op.inputs.streams_container.connect(my_streams_container)
my_ProducedFile = op.outputs.ProducedFile()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.FileName.Connect(my_FileName)
op.inputs.RightHandSide.Connect(my_RightHandSide)
op.inputs.streams_container.Connect(my_streams_container)
my_ProducedFile = op.outputs.ProducedFile.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.