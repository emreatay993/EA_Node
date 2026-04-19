---
category: utility
plugin: core
license: None
---

# utility:transpose fields container

**Version: 0.0.0**

## Description

Transpose a fields container: each fields scoping becomes the fields container's scoping and the time scoping (or the label chosen) becomes the fields' scopings. Each field must have same scoping ids and location. Performance optimized for 1 or 2 labels FieldsContainer.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | It is assumed that the fields container consists of fields having the same scoping. |
| <strong>Pin 1</strong>|  label |[`string`](../../core-concepts/dpf-types.md#standard-types) | fields container label to use as fields lable (default is time) |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: transpose_fields_container

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("transpose_fields_container"); // operator instantiation
op.connect(0, my_fields_container);
op.connect(1, my_label);
ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.fields_container.connect(my_fields_container)
op.inputs.label.connect(my_label)
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.None() # operator instantiation
op.inputs.fields_container.Connect(my_fields_container)
op.inputs.label.Connect(my_label)
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.