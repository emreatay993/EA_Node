---
category: None
plugin: core
license: None
---

# apply mapping

**Version: 0.0.0**

## Description

Takes mapping data and uses it to map input results (pin 0) on output support (pin 1).

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mapping_data |[`MappingData`](../../core-concepts/dpf-types.md#mappingdata) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  values |[`field`](../../core-concepts/dpf-types.md#field), [`fields_container`](../../core-concepts/dpf-types.md#fields-container) | A field defined on the input support. |
| <strong>Pin 2</strong>|  output_support |[`field`](../../core-concepts/dpf-types.md#field), [`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) | Output support (where we will interpolate the results). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| field |[`field`](../../core-concepts/dpf-types.md#field), [`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: apply_mapping

 **Full name**: None

 **Internal name**: apply_mapping

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("apply_mapping"); // operator instantiation
op.connect(0, my_mapping_data);
op.connect(1, my_values);
op.connect(2, my_output_support);
ansys::dpf::Field my_field = op.getOutput<ansys::dpf::Field>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.apply_mapping() # operator instantiation
op.inputs.mapping_data.connect(my_mapping_data)
op.inputs.values.connect(my_values)
op.inputs.output_support.connect(my_output_support)
my_field_as_field = op.outputs.field_as_field()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.apply_mapping() # operator instantiation
op.inputs.mapping_data.Connect(my_mapping_data)
op.inputs.values.Connect(my_values)
op.inputs.output_support.Connect(my_output_support)
my_field = op.outputs.field.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.