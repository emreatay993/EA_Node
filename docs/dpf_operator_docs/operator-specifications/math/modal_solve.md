---
category: math
plugin: core
license: None
---

# math:modal solve 

**Version: 0.0.0**

## Description

Computes the time or frequency response using modal superposition method.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_containerA |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | input field container expects mode shapes |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  natural_freq |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | input vector expects natural frequencies |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  rhs |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | field container expects rhs. When rhs contains the input_dof_index label, the solve is made for each label separately and RHS values will be unitary for each dof_index.When it does not, RHS must have the same number of components than mode shapes.When the RHS has a time/frequency support, a linear interpolation is performed to evaluate it at requested time_freq_support frequencies.When it does not, the time/frequency sets of the RHS must match the time/frequency steps requested as no interpolation is performed. |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  output_mesh_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) | output scoping |
| <strong>Pin 5</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  output_number_of_components_by_ids |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`int32`](../../core-concepts/dpf-types.md#standard-types) | number of output component |
| <strong>Pin 6</strong>|  output_component_number_by_ids |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | Output component number. If not specified, component number will go from 0 to the number of components - 1 for each ID by default. |
| <strong>Pin 7</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  damping |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | this pin expects vector of modal damping coefficients (coefficient per modes). |
| <strong>Pin 8</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  time_freq_support |[`time_freq_support`](../../core-concepts/dpf-types.md#time-freq-support) | Time Freq to integrate on. |
| <strong>Pin 9</strong>|  input_type |[`int32`](../../core-concepts/dpf-types.md#standard-types) | if this pin is set to 1, time response is computed. Pin set to 0, frequency response is computed. By default frequency response is computed. |
| <strong>Pin 10</strong>|  velocity_and_acceleration |[`bool`](../../core-concepts/dpf-types.md#standard-types) | if this pin is set to true, the velocity and the acceleration is computed. |
| <strong>Pin 11</strong>|  modal_coordinates |[`bool`](../../core-concepts/dpf-types.md#standard-types) | if this pin is set to true, the modal coordinates can be retrieved in pin 3. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_containerA |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | displacement fields container of the time/freq response |
|  **Pin 1**| fields_containerB |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | velocity fields container of the time/freq response |
|  **Pin 2**| fields_containerC |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | acceleration fields container of the time/freq response |
|  **Pin 3**| modal_coordinates |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | fields container of the modal coordinates. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **sampling_options_error** |[`vector<double>`](../../core-concepts/dpf-types.md#standard-types) | (1;0.001) | Option values to use sampling: minimum step size and absolute error value, respectively. |
| **sampling_options_norm** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Option value to define the norm : value 0 for NormInf, value 1 for Norm2.  |
| **use_sampling** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the time or frequency response is allowed to use the sampling method. With the sampling method, the load vector needs to be constant across time/frequency range. |

## Scripting

 **Category**: math

 **Plugin**: core

 **Scripting name**: modal_solve

 **Full name**: math.modal_solve

 **Internal name**: modal_solve

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("modal_solve"); // operator instantiation
op.connect(0, my_fields_containerA);
op.connect(1, my_natural_freq);
op.connect(3, my_rhs);
op.connect(4, my_output_mesh_scoping);
op.connect(5, my_output_number_of_components_by_ids);
op.connect(6, my_output_component_number_by_ids);
op.connect(7, my_damping);
op.connect(8, my_time_freq_support);
op.connect(9, my_input_type);
op.connect(10, my_velocity_and_acceleration);
op.connect(11, my_modal_coordinates);
ansys::dpf::FieldsContainer my_fields_containerA = op.getOutput<ansys::dpf::FieldsContainer>(0);
ansys::dpf::FieldsContainer my_fields_containerB = op.getOutput<ansys::dpf::FieldsContainer>(1);
ansys::dpf::FieldsContainer my_fields_containerC = op.getOutput<ansys::dpf::FieldsContainer>(2);
ansys::dpf::FieldsContainer my_modal_coordinates = op.getOutput<ansys::dpf::FieldsContainer>(3);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.math.modal_solve() # operator instantiation
op.inputs.fields_containerA.connect(my_fields_containerA)
op.inputs.natural_freq.connect(my_natural_freq)
op.inputs.rhs.connect(my_rhs)
op.inputs.output_mesh_scoping.connect(my_output_mesh_scoping)
op.inputs.output_number_of_components_by_ids.connect(my_output_number_of_components_by_ids)
op.inputs.output_component_number_by_ids.connect(my_output_component_number_by_ids)
op.inputs.damping.connect(my_damping)
op.inputs.time_freq_support.connect(my_time_freq_support)
op.inputs.input_type.connect(my_input_type)
op.inputs.velocity_and_acceleration.connect(my_velocity_and_acceleration)
op.inputs.modal_coordinates.connect(my_modal_coordinates)
my_fields_containerA = op.outputs.fields_containerA()
my_fields_containerB = op.outputs.fields_containerB()
my_fields_containerC = op.outputs.fields_containerC()
my_modal_coordinates = op.outputs.modal_coordinates()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.math.modal_solve() # operator instantiation
op.inputs.fields_containerA.Connect(my_fields_containerA)
op.inputs.natural_freq.Connect(my_natural_freq)
op.inputs.rhs.Connect(my_rhs)
op.inputs.output_mesh_scoping.Connect(my_output_mesh_scoping)
op.inputs.output_number_of_components_by_ids.Connect(my_output_number_of_components_by_ids)
op.inputs.output_component_number_by_ids.Connect(my_output_component_number_by_ids)
op.inputs.damping.Connect(my_damping)
op.inputs.time_freq_support.Connect(my_time_freq_support)
op.inputs.input_type.Connect(my_input_type)
op.inputs.velocity_and_acceleration.Connect(my_velocity_and_acceleration)
op.inputs.modal_coordinates.Connect(my_modal_coordinates)
my_fields_containerA = op.outputs.fields_containerA.GetData()
my_fields_containerB = op.outputs.fields_containerB.GetData()
my_fields_containerC = op.outputs.fields_containerC.GetData()
my_modal_coordinates = op.outputs.modal_coordinates.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.