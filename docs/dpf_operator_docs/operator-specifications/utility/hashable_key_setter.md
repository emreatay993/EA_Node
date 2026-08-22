---
category: utility
plugin: core
license: None
---

# utility:hashable key setter

**Version: 0.0.0**

## Description

Setter for hashable key of a dpf entity.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  dpf_entity |[`workflow`](../../core-concepts/dpf-types.md#workflow), [`data_sources`](../../core-concepts/dpf-types.md#data-sources), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  hashable_key |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: hashable_key_setter

 **Full name**: utility.hashable_key_setter

 **Internal name**: hashable_key_setter

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("hashable_key_setter"); // operator instantiation
op.connect(0, my_dpf_entity);
op.connect(1, my_hashable_key);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.hashable_key_setter() # operator instantiation
op.inputs.dpf_entity.connect(my_dpf_entity)
op.inputs.hashable_key.connect(my_hashable_key)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.hashable_key_setter() # operator instantiation
op.inputs.dpf_entity.Connect(my_dpf_entity)
op.inputs.hashable_key.Connect(my_hashable_key)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.