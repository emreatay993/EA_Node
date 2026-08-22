---
category: utility
plugin: core
license: None
---

# utility:forward to generic data container

**Version: 0.0.0**

## Description

Generates a generic data container from provided information.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  input_name |[`string`](../../core-concepts/dpf-types.md#standard-types), [`any`](../../core-concepts/dpf-types.md#any) | Set of even and odd pins to add Generic Data Container items. Odd pins (0, 2, 4...) are strings, and they represent the names of the DPF types to be inserted in the GDC. Even pins (1, 3, 5...) are DPF types, and they represent the objects to be included. They should go in pairs (for each name, there should be an object) and connected sequentially. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| generic_data_container |[`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: forward_to_gdc

 **Full name**: utility.forward_to_gdc

 **Internal name**: forward_to_gdc

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("forward_to_gdc"); // operator instantiation
op.connect(0, my_input_name);
ansys::dpf::GenericDataContainer my_generic_data_container = op.getOutput<ansys::dpf::GenericDataContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.forward_to_gdc() # operator instantiation
op.inputs.input_name1.connect(my_input_name1)
op.inputs.input_name2.connect(my_input_name2)
my_generic_data_container = op.outputs.generic_data_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.forward_to_gdc() # operator instantiation
op.inputs.input_name.Connect(my_input_name)
my_generic_data_container = op.outputs.generic_data_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.