---
category: utility
plugin: core
license: None
---

# utility:homogeneity string from id

**Version: 0.0.0**

## Description

Returns the homogeneity string from the homogeneity ID.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  homogeneity_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Homogeneity ID |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| homogeneity_string |[`string`](../../core-concepts/dpf-types.md#standard-types) | Homogeneity string |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: homogeneity_string_from_id

 **Full name**: utility.homogeneity_string_from_id

 **Internal name**: homogeneity_string_from_id

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("homogeneity_string_from_id"); // operator instantiation
op.connect(0, my_homogeneity_id);
std::string my_homogeneity_string = op.getOutput<std::string>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.homogeneity_string_from_id() # operator instantiation
op.inputs.homogeneity_id.connect(my_homogeneity_id)
my_homogeneity_string = op.outputs.homogeneity_string()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.homogeneity_string_from_id() # operator instantiation
op.inputs.homogeneity_id.Connect(my_homogeneity_id)
my_homogeneity_string = op.outputs.homogeneity_string.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.