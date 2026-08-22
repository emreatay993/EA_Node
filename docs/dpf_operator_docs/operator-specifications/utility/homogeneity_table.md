---
category: utility
plugin: core
license: None
---

# utility:homogeneity table

**Version: 0.0.0**

## Description

Returns the homogeneity table as an StringField, with the strings being in the format expected by pydpf-core.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| homogeneity_table |[`string_field`](../../core-concepts/dpf-types.md#string-field) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: homogeneity_table

 **Full name**: utility.homogeneity_table

 **Internal name**: homogeneity_table

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("homogeneity_table"); // operator instantiation
ansys::dpf::StringField my_homogeneity_table = op.getOutput<ansys::dpf::StringField>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.homogeneity_table() # operator instantiation
my_homogeneity_table = op.outputs.homogeneity_table()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.homogeneity_table() # operator instantiation
my_homogeneity_table = op.outputs.homogeneity_table.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.