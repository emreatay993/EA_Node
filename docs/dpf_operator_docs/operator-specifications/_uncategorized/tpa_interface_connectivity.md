---
category: None
plugin: N/A
license: None
---

# tpa::interface_connectivity

**Version: 0.0.0**

## Description

Computes the matrix B representing the connectivity between interface dofs of Transfer Path Analysis (TPA) components as a fields container.
                                                                                                                                     
Example: 3 components connected through 2 interfaces with 3 dofs per interface                                                       
-------                                                                                                                              
       -------- ---           --- -------- ---           --- --------                                                                
     ||        | 0 || ----> || 1 |        | 3 || ----> || 1 |        ||                                                              
 --> || COMP 1 | 1 || ----> || 0 | COMP 2 | 4 || ----> || 0 | COMP 3 || -->                                                          
     ||        | 2 || ----> || 2 |        | 5 || ----> || 2 |        ||                                                              
       -------- ---           --- -------- ---           --- --------                                                                
  UPSTREAM                                                         DOWNSTREAM                                                        
                                                                                                                                     
 The following table must be input to the operator to generate connectivity matrices B1, B2 and B3                                   
                                                                                                                                     
| Scoping ID | Upstream component ID | Upstream component DOF | Downstream component ID | Downstream component DOF |                 
|------------|-----------------------|------------------------|-------------------------|--------------------------|                 
|     0      |            1          |           0            |             2           |              1           |                 
|     1      |            1          |           1            |             2           |              0           | --> Interface 1 
|     2      |            1          |           2            |             2           |              2           |                 
|------------------------------------------------------------------------------------------------------------------|                 
|     3      |            2          |           3            |             3           |              1           |                 
|     4      |            2          |           4            |             3           |              0           | --> Interface 2 
|     5      |            2          |           5            |             3           |              2           |                 
|------------------------------------------------------------------------------------------------------------------|                 
                                                                                                                                     
 The corresponding output B matrices will be:                                                                                        
      | -1   0   0  |        | 0  1  0   0   0   0 |        | 0  0  0  |                                                             
      |  0  -1   0  |        | 1  0  0   0   0   0 |        | 0  0  0  |                                                             
      |  0   0  -1  |        | 0  0  1   0   0   0 |        | 0  0  0  |                                                             
 B1 = |  0   0   0  |   B2 = | 0  0  0  -1   0   0 |   B3 = | 0  1  0  |                                                             
      |  0   0   0  |        | 0  0  0   0  -1   0 |        | 1  0  0  |                                                             
      |  0   0   0  |        | 0  0  0   0   0  -1 |        | 0  0  1  |                                                             


## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  upstream_component_id |[`property_field`](../../core-concepts/dpf-types.md#property-field) | Property field containing the upstream component ID for each interface dof pair of the whole TPA model. The scoping and the data length should be the same as in input pins 1, 2 and 3. |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  upstream_component_dof |[`property_field`](../../core-concepts/dpf-types.md#property-field) | Property field containing the upstream component dof number for each interface dof pair of the whole TPA model. The scoping and the data length should be the same as in input pins 0, 2 and 3. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  downstream_component_id |[`property_field`](../../core-concepts/dpf-types.md#property-field) | Property field containing the downstream component ID for each interface dof pair of the whole TPA model. The scoping and the data length should be the same as in input pins 0, 1 and 3. |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  downstream_component_dof |[`property_field`](../../core-concepts/dpf-types.md#property-field) | Property field containing the upstream component dof number for each interface dof pair of the whole TPA model. The scoping and the data length should be the same as in input pins 0, 1 and 2. |
| <strong>Pin 4</strong>|  is_complex |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Boolean value to select if output must be complex (default) or real. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| B_matrix |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container storing the columns of the connectivity matrix B for each TPA component. "
The fields container is organized as follows: for a given component (label "component"), each field represents a column of matrix B (label "column"). If is_complex = true, a "complex" label is added to the label space.  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: tpa::interface_connectivity

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("tpa::interface_connectivity"); // operator instantiation
op.connect(0, my_upstream_component_id);
op.connect(1, my_upstream_component_dof);
op.connect(2, my_downstream_component_id);
op.connect(3, my_downstream_component_dof);
op.connect(4, my_is_complex);
ansys::dpf::FieldsContainer my_B_matrix = op.getOutput<ansys::dpf::FieldsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.upstream_component_id.connect(my_upstream_component_id)
op.inputs.upstream_component_dof.connect(my_upstream_component_dof)
op.inputs.downstream_component_id.connect(my_downstream_component_id)
op.inputs.downstream_component_dof.connect(my_downstream_component_dof)
op.inputs.is_complex.connect(my_is_complex)
my_B_matrix = op.outputs.B_matrix()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.upstream_component_id.Connect(my_upstream_component_id)
op.inputs.upstream_component_dof.Connect(my_upstream_component_dof)
op.inputs.downstream_component_id.Connect(my_downstream_component_id)
op.inputs.downstream_component_dof.Connect(my_downstream_component_dof)
op.inputs.is_complex.Connect(my_is_complex)
my_B_matrix = op.outputs.B_matrix.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.