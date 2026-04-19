---
category: None
plugin: core
license: None
---

# cyclic_expansion_field

**Version: 0.0.0**

## Description

Expand a field with cyclic symmetry

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  base_sector |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  duplicate_sector |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  harmonic_index |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mesh_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) |  |
| <strong>Pin 6</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  stage_index |[`int32`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 7</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  normalization_factor |[`double`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 16</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  cyclic_support |[`cyclic_support`](../../core-concepts/dpf-types.md#cyclic-support) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| field |[`field`](../../core-concepts/dpf-types.md#field) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |
| **num_threads** |[`int32`](../../core-concepts/dpf-types.md#standard-types) | 0 | Number of threads to use to run in parallel |
| **run_in_parallel** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Loops are allowed to run in parallel if the value of this config is set to true. |
| **use_cache** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | true | Some intermediate data is put in cache if this config is set to true. This option can reduce computation time after the first run. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cyclic_expansion_field

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cyclic_expansion_field"); // operator instantiation
op.connect(0, my_base_sector);
op.connect(1, my_duplicate_sector);
op.connect(3, my_harmonic_index);
op.connect(4, my_mesh_scoping);
op.connect(6, my_stage_index);
op.connect(7, my_normalization_factor);
op.connect(16, my_cyclic_support);
ansys::dpf::Field my_field = op.getOutput<ansys::dpf::Field>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.base_sector.connect(my_base_sector)
op.inputs.duplicate_sector.connect(my_duplicate_sector)
op.inputs.harmonic_index.connect(my_harmonic_index)
op.inputs.mesh_scoping.connect(my_mesh_scoping)
op.inputs.stage_index.connect(my_stage_index)
op.inputs.normalization_factor.connect(my_normalization_factor)
op.inputs.cyclic_support.connect(my_cyclic_support)
my_field = op.outputs.field()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.base_sector.Connect(my_base_sector)
op.inputs.duplicate_sector.Connect(my_duplicate_sector)
op.inputs.harmonic_index.Connect(my_harmonic_index)
op.inputs.mesh_scoping.Connect(my_mesh_scoping)
op.inputs.stage_index.Connect(my_stage_index)
op.inputs.normalization_factor.Connect(my_normalization_factor)
op.inputs.cyclic_support.Connect(my_cyclic_support)
my_field = op.outputs.field.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.