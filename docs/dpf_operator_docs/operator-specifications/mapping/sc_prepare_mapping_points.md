---
category: mapping
plugin: N/A
license: None
---

# mapping:sc_prepare_mapping_points

**Version: 0.0.0**

## Description

Precomputes Mapping data to enhance performance for PointCloud-based interpolation

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  source_coords |[`field`](../../core-concepts/dpf-types.md#field), [`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Coordinates where the source data is defined. |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  target_coords |[`field`](../../core-concepts/dpf-types.md#field), [`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Coordinates where the target data is defined. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  is_conservative |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Boolean that indicates if the mapped variable is conservative (e.g. force) or not (e.g. pressure). |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  dimensionality |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Dimensionality of the mapped variable. Supported options: 1 and 3 (scalars or vectors) |
| <strong>Pin 6</strong>|  target_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping), [`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | Scoping that restricts the interpolation to a given set of nodes/elements in the target coords. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| sc_counter | | sc counter to keep track |
|  **Pin 1**| source_scoping |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | Source scoping |
|  **Pin 2**| target_scoping |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | Target scoping |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: mapping

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: sc_prepare_mapping_points

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("sc_prepare_mapping_points"); // operator instantiation
op.connect(0, my_source_coords);
op.connect(1, my_target_coords);
op.connect(2, my_is_conservative);
op.connect(4, my_dimensionality);
op.connect(6, my_target_scoping);
 my_sc_counter = op.getOutput<>(0);
ansys::dpf::ScopingsContainer my_source_scoping = op.getOutput<ansys::dpf::ScopingsContainer>(1);
ansys::dpf::ScopingsContainer my_target_scoping = op.getOutput<ansys::dpf::ScopingsContainer>(2);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.mapping.None() # operator instantiation
op.inputs.source_coords.connect(my_source_coords)
op.inputs.target_coords.connect(my_target_coords)
op.inputs.is_conservative.connect(my_is_conservative)
op.inputs.dimensionality.connect(my_dimensionality)
op.inputs.target_scoping.connect(my_target_scoping)
my_sc_counter = op.outputs.sc_counter()
my_source_scoping = op.outputs.source_scoping()
my_target_scoping = op.outputs.target_scoping()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.mapping.None() # operator instantiation
op.inputs.source_coords.Connect(my_source_coords)
op.inputs.target_coords.Connect(my_target_coords)
op.inputs.is_conservative.Connect(my_is_conservative)
op.inputs.dimensionality.Connect(my_dimensionality)
op.inputs.target_scoping.Connect(my_target_scoping)
my_sc_counter = op.outputs.sc_counter.GetData()
my_source_scoping = op.outputs.source_scoping.GetData()
my_target_scoping = op.outputs.target_scoping.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.