---
category: result
plugin: mapdl
license: None
---

# result:mapdl::element_records_properties_provider

**Version: 0.0.0**

## Description

Exposes general metadata about elemental records of MAPDL.
The output of this operator does not change between calls, but may be different between two versions of DPF.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  element_records_properties |[`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) | List of the supported results. It's a generic data containers of type `ElementRcordsProperties`.<br>It contains a child GenericDataContainer under the key "results" where each key is the common record name (ENS, EUL, ...) and each value contains the following metadata:<br>- `class_name` (string): "ElementRecordProperty"<br>- `number_of_components` (integer): Number of components of in the record in the general case.<br>- `additional_size` (integer): Extra size not by component<br>- `location` (string): Location, one of the value supported by ansys::dpf::Location<br>- `record_identifier` (integer): Unique identifier of the result. It's the index from 0 to 25 ordered like in result files. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::element_records_properties_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::element_records_properties_provider"); // operator instantiation
op.connect(0, my_element_records_properties);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.element_records_properties.connect(my_element_records_properties)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.element_records_properties.Connect(my_element_records_properties)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.