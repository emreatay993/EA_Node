---
category: None
plugin: core
license: None
---

# scoping::expanded_cyclic

**Version: 0.0.0**

## Description

Expand scopings (nodal or elemental default is elemental) on one sector to a list of sectors or all the sectors depending on the cyclic support.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  mesh_scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping), [`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |
| <strong>Pin 16</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  cyclic_support |[`cyclic_support`](../../core-concepts/dpf-types.md#cyclic-support) |  |
| <strong>Pin 18</strong>|  sectors_to_expand |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | sectors to expand (start at 0), for multistage: use scopings container with 'stage' label. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| scopings_container |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: scoping::expanded_cyclic

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("scoping::expanded_cyclic"); // operator instantiation
op.connect(1, my_mesh_scoping);
op.connect(16, my_cyclic_support);
op.connect(18, my_sectors_to_expand);
ansys::dpf::ScopingsContainer my_scopings_container = op.getOutput<ansys::dpf::ScopingsContainer>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.mesh_scoping.connect(my_mesh_scoping)
op.inputs.cyclic_support.connect(my_cyclic_support)
op.inputs.sectors_to_expand.connect(my_sectors_to_expand)
my_scopings_container = op.outputs.scopings_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.mesh_scoping.Connect(my_mesh_scoping)
op.inputs.cyclic_support.Connect(my_cyclic_support)
op.inputs.sectors_to_expand.Connect(my_sectors_to_expand)
my_scopings_container = op.outputs.scopings_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.