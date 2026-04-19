---
category: utility
plugin: core
license: None
---

# utility:hashable key getter

**Version: 0.0.0**

## Description

Getter for hashable key of a dpf entity.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  dpf_entity |[`workflow`](../../core-concepts/dpf-types.md#workflow), [`data_sources`](../../core-concepts/dpf-types.md#data-sources), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| hashable_key |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: hashable_key_getter

 **Full name**: utility.hashable_key_getter

 **Internal name**: hashable_key_getter

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("hashable_key_getter"); // operator instantiation
op.connect(0, my_dpf_entity);
std::string my_hashable_key = op.getOutput<std::string>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.hashable_key_getter() # operator instantiation
op.inputs.dpf_entity.connect(my_dpf_entity)
my_hashable_key = op.outputs.hashable_key()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.hashable_key_getter() # operator instantiation
op.inputs.dpf_entity.Connect(my_dpf_entity)
my_hashable_key = op.outputs.hashable_key.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.