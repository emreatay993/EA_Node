---
category: metadata
plugin: core
license: None
---

# metadata:filter element types

**Version: 0.0.0**

## Description

Takes a PropertyField representing ElementTypesProperties and produces either a GenericDataContainer or a PropertyField (based on input 200) with the solver element type ids from input 1.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  property_field |[`property_field`](../../core-concepts/dpf-types.md#property-field) | PropertyField with all ElementTypesProperties for all solver element type ids. |
| <strong>Pin 1</strong>|  solver_element_types_ids |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | Element Type ids to recover used by the solver. If not set, all available element types are recovered. |
| <strong>Pin 200</strong>|  output_type |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Get the output as a GenericDataContainer (pin value 1, default) or as a PropertyField (pin value 2). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| element_types_data |[`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container), [`property_field`](../../core-concepts/dpf-types.md#property-field) | 
- If the output is a GenericDataContainer, its class_name is ElementTypesProperties and it contains the following property fields:
  - element_routine_number: Element routine number. E.g 186 for SOLID186.
  - keyopts: Element type option keys.
  - kdofs: DOF/node for this element type. This is a bit mapping.
  - nodelm: Number of nodes for this element type.
  - nodfor: Number of nodes per element having nodal forces.
  - nodstr: Number of nodes per element having nodal stresses.
  - new_gen_element: Element of new generation.
- If the output is a PropertyField, it contains the 200 possible ElementTypesProperties for each solver element type id. These properties are in the order documented in ansys/customize/include/echprm.inc and have the meaning documented in ansys/customize/include/elccmt.inc. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: filter_element_types

 **Full name**: metadata.filter_element_types

 **Internal name**: filter_element_types

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("filter_element_types"); // operator instantiation
op.connect(0, my_property_field);
op.connect(1, my_solver_element_types_ids);
op.connect(200, my_output_type);
ansys::dpf::GenericDataContainer my_element_types_data = op.getOutput<ansys::dpf::GenericDataContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.filter_element_types() # operator instantiation
op.inputs.property_field.connect(my_property_field)
op.inputs.solver_element_types_ids.connect(my_solver_element_types_ids)
op.inputs.output_type.connect(my_output_type)
my_element_types_data_as_generic_data_container = op.outputs.element_types_data_as_generic_data_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.filter_element_types() # operator instantiation
op.inputs.property_field.Connect(my_property_field)
op.inputs.solver_element_types_ids.Connect(my_solver_element_types_ids)
op.inputs.output_type.Connect(my_output_type)
my_element_types_data = op.outputs.element_types_data.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.