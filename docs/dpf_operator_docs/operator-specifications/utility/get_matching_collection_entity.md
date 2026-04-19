---
category: utility
plugin: core
license: None
---

# utility:get matching collection entity

**Version: 0.0.0**

## Description

Gets the collection A entity that matches the label space.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  collection_A |[`any_collection`](../../core-concepts/dpf-types.md#any-collection), [`scopings_container`](../../core-concepts/dpf-types.md#scopings-container), [`fields_container`](../../core-concepts/dpf-types.md#fields-container), [`property_fields_container`](../../core-concepts/dpf-types.md#property-fields-container), [`custom_type_fields_container`](../../core-concepts/dpf-types.md#custom-type-fields-container), [`meshes_container`](../../core-concepts/dpf-types.md#meshes-container) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  label_space |[`impl_label_space`](../../core-concepts/dpf-types.md#impl-label-space) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| output |[`any`](../../core-concepts/dpf-types.md#any), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`field`](../../core-concepts/dpf-types.md#field), [`property_field`](../../core-concepts/dpf-types.md#property-field), [`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field), [`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: get_matching_collection_entity

 **Full name**: utility.get_matching_collection_entity

 **Internal name**: collection::get_matching_collection_entity

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("collection::get_matching_collection_entity"); // operator instantiation
op.connect(0, my_collection_A);
op.connect(1, my_label_space);
ansys::dpf::Any my_output = op.getOutput<ansys::dpf::Any>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.get_matching_collection_entity() # operator instantiation
op.inputs.collection_A.connect(my_collection_A)
op.inputs.label_space.connect(my_label_space)
my_output_as_any = op.outputs.output_as_any()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.get_matching_collection_entity() # operator instantiation
op.inputs.collection_A.Connect(my_collection_A)
op.inputs.label_space.Connect(my_label_space)
my_output = op.outputs.output.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.