---
category: None
plugin: mapdl
license: None
---

# mapdl rst mesh setter

**Version: 0.0.0**

## Description

Sets a mesh in the _meshes object of the rst stream

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | result file container allowed to be kept open to cache data |
| <strong>Pin 7</strong>|  abstract_meshed_region |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) | prevents from reading the mesh in the result files |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::rst::mesh_setter

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::rst::mesh_setter"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(7, my_abstract_meshed_region);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.abstract_meshed_region.connect(my_abstract_meshed_region)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.abstract_meshed_region.Connect(my_abstract_meshed_region)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.