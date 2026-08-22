---
category: result
plugin: mapdl
license: None
---

# result:mapdl::element_results_properties_provider

**Version: 0.0.0**

## Description

Exposes general metadata about elemental and elemental nodal results of MAPL. 
The output of this operator does not change between calls, but may be different between two versions of DPF.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  element_results_properties |[`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) | List of the supported results. It's a generic data containers of type `ElementResultsProperties`.<br>It contains a child GenericDataContainer under the key "results" where each key is the common result name (S, ENF, ...) and each value contains the following metadata:<br>- `class_name` (string): "ElementResultProperty"<br>- `record` (string): The record name in the elemental dataset. The metadata of the records can be retrieved with `mapdl::element_records_properties_provider`<br>- `number_of_components` (integer): Number of components of the result exposed to the caller<br>- `location` (string): Location, one of the value supported by ansys::dpf::Location<br>- `homogeneity` (string): Homogeneity, one of the value supported by ansys::dpf::Homogeneity<br>- `description` (string): User facing description<br>- `result_identifier` (integer): Unique identifier of the result |

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

 **Internal name**: mapdl::element_results_properties_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::element_results_properties_provider"); // operator instantiation
op.connect(0, my_element_results_properties);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.element_results_properties.connect(my_element_results_properties)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.element_results_properties.Connect(my_element_results_properties)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.