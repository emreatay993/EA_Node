---
category: None
plugin: core
license: any_dpf_supported_increments
---

# nodal extend to mid nodes (field)

**Version: 0.0.0**

## Description

Extends a Nodal field defined on corner nodes to a field defined also on mid nodes.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field |[`field`](../../core-concepts/dpf-types.md#field), [`fields_container`](../../core-concepts/dpf-types.md#fields-container) | field or fields container with only one field is expected |
| <strong>Pin 1</strong>|  node_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) | Nodes expected in output. |
| <strong>Pin 5</strong>|  element_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) | Precomputed list of elements of interest (improves performances). |
| <strong>Pin 7</strong>|  mesh |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| field |[`field`](../../core-concepts/dpf-types.md#field) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **inplace** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | The output is written over the input to save memory if this config is set to true. |
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: nodal_extend_to_mid_nodes

 **Full name**: None

 **Internal name**: nodal_extend_to_mid_nodes

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("nodal_extend_to_mid_nodes"); // operator instantiation
op.connect(0, my_field);
op.connect(1, my_node_scoping);
op.connect(5, my_element_scoping);
op.connect(7, my_mesh);
ansys::dpf::Field my_field = op.getOutput<ansys::dpf::Field>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.nodal_extend_to_mid_nodes() # operator instantiation
op.inputs.field.connect(my_field)
op.inputs.node_scoping.connect(my_node_scoping)
op.inputs.element_scoping.connect(my_element_scoping)
op.inputs.mesh.connect(my_mesh)
my_field = op.outputs.field()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.nodal_extend_to_mid_nodes() # operator instantiation
op.inputs.field.Connect(my_field)
op.inputs.node_scoping.Connect(my_node_scoping)
op.inputs.element_scoping.Connect(my_element_scoping)
op.inputs.mesh.Connect(my_mesh)
my_field = op.outputs.field.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.