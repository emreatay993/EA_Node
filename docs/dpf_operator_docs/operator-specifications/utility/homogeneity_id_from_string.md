---
category: utility
plugin: core
license: None
---

# utility:homogeneity id from string

**Version: 0.0.0**

## Description

Returns the homogeneity ID as an integer from the homogeneity string.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  homogeneity_string |[`string`](../../core-concepts/dpf-types.md#standard-types) | Homogeneity as a string |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| homogeneity_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Homogeneity ID |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: homogeneity_id_from_string

 **Full name**: utility.homogeneity_id_from_string

 **Internal name**: homogeneity_id_from_string

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("homogeneity_id_from_string"); // operator instantiation
op.connect(0, my_homogeneity_string);
int my_homogeneity_id = op.getOutput<int>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.homogeneity_id_from_string() # operator instantiation
op.inputs.homogeneity_string.connect(my_homogeneity_string)
my_homogeneity_id = op.outputs.homogeneity_id()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.homogeneity_id_from_string() # operator instantiation
op.inputs.homogeneity_string.Connect(my_homogeneity_string)
my_homogeneity_id = op.outputs.homogeneity_id.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.