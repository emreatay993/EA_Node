---
category: min_max
plugin: core
license: any_dpf_supported_increments
---

# min_max:max_nodal_dif

**Version: 0.0.0**

## Description

max nodal diff result

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field |[`field`](../../core-concepts/dpf-types.md#field), [`fields_container`](../../core-concepts/dpf-types.md#fields-container) | field or fields container with only one field is expected |
| <strong>Pin 1</strong>|  scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) | the max nodal diff is computed only on the nodes in this scoping |
| <strong>Pin 2</strong>|  include_mid_nodes |[`bool`](../../core-concepts/dpf-types.md#standard-types) | ignore or include the mid side nodes in the max nodal diff calculation |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| field |[`field`](../../core-concepts/dpf-types.md#field) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: min_max

 **Plugin**: core

 **Scripting name**: max_nodal_dif

 **Full name**: min_max.max_nodal_dif

 **Internal name**: max_nodal_diff

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("max_nodal_diff"); // operator instantiation
op.connect(0, my_field);
op.connect(1, my_scoping);
op.connect(2, my_include_mid_nodes);
ansys::dpf::Field my_field = op.getOutput<ansys::dpf::Field>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.min_max.max_nodal_dif() # operator instantiation
op.inputs.field.connect(my_field)
op.inputs.scoping.connect(my_scoping)
op.inputs.include_mid_nodes.connect(my_include_mid_nodes)
my_field = op.outputs.field()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.min_max.max_nodal_dif() # operator instantiation
op.inputs.field.Connect(my_field)
op.inputs.scoping.Connect(my_scoping)
op.inputs.include_mid_nodes.Connect(my_include_mid_nodes)
my_field = op.outputs.field.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.