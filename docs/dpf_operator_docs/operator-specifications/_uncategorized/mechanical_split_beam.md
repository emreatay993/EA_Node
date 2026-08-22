---
category: None
plugin: N/A
license: None
---

# mechanical split beam

**Version: 0.0.0**

## Description

Takes an input FieldsContainer and splits the Fields based on its mesh support.If the mesh support only has beam elements, the Field is placed in output 1. If not, it is placed in output 0.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container to split containing beam and non-beam results. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| non_beam_fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container containing non-beam results. |
|  **Pin 1**| beam_fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container containing beam results. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: mechanical_split_beam

 **Full name**: None

 **Internal name**: mechanical::split_beam

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical::split_beam"); // operator instantiation
op.connect(0, my_fields_container);
ansys::dpf::FieldsContainer my_non_beam_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
ansys::dpf::FieldsContainer my_beam_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.mechanical_split_beam() # operator instantiation
op.inputs.fields_container.connect(my_fields_container)
my_non_beam_fields_container = op.outputs.non_beam_fields_container()
my_beam_fields_container = op.outputs.beam_fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.mechanical_split_beam() # operator instantiation
op.inputs.fields_container.Connect(my_fields_container)
my_non_beam_fields_container = op.outputs.non_beam_fields_container.GetData()
my_beam_fields_container = op.outputs.beam_fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.