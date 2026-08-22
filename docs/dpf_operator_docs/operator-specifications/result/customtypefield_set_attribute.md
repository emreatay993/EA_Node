---
category: result
plugin: core
license: None
---

# result:customtypefield::set_attribute

**Version: 0.0.0**

## Description

Sets a property to an input field/field container. A CustomTypeFieldin pin 0, a property name (string) in pin 1 and a valid property value in pin 2 are expected as inputs

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  custom_type_field |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field), [`custom_type_fields_container`](../../core-concepts/dpf-types.md#custom-type-fields-container) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  property_name |[`string`](../../core-concepts/dpf-types.md#standard-types) | Property to set. Accepted inputs are specific strings namely: 'unit', 'name', 'time_freq_support', 'scoping', 'header'. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  property |[`string`](../../core-concepts/dpf-types.md#standard-types), [`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree), [`int32`](../../core-concepts/dpf-types.md#standard-types), [`double`](../../core-concepts/dpf-types.md#standard-types) | Property Value to set. Accepted inputs on this pin are: CTimeFreqSupport, CScoping, DataTree, int, double, string. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| field |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field), [`custom_type_fields_container`](../../core-concepts/dpf-types.md#custom-type-fields-container) | Accepted Outputs are: Field, PropertyField, CustomTypeField or their containers. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: customtypefield::set_attribute

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("customtypefield::set_attribute"); // operator instantiation
op.connect(0, my_custom_type_field);
op.connect(1, my_property_name);
op.connect(2, my_property);
ansys::dpf::CustomTypeField my_field = op.getOutput<ansys::dpf::CustomTypeField>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.custom_type_field.connect(my_custom_type_field)
op.inputs.property_name.connect(my_property_name)
op.inputs.property.connect(my_property)
my_field_as_custom_type_field = op.outputs.field_as_custom_type_field()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.custom_type_field.Connect(my_custom_type_field)
op.inputs.property_name.Connect(my_property_name)
op.inputs.property.Connect(my_property)
my_field = op.outputs.field.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.