---
category: utility
plugin: core
license: None
---

# utility:custom unit

**Version: 0.0.0**

## Description

Gets unit symbol from a set of unit strings.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  unit_strings |[`string`](../../core-concepts/dpf-types.md#standard-types) | Semicolon separated list of base units or ansys unit system's ID |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  homogeneity |[`string`](../../core-concepts/dpf-types.md#standard-types) | Homogeneity of the desired unit |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| unit_symbol |[`string`](../../core-concepts/dpf-types.md#standard-types) | Unit Symbol |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: custom_unit

 **Full name**: utility.custom_unit

 **Internal name**: custom_unit

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("custom_unit"); // operator instantiation
op.connect(0, my_unit_strings);
op.connect(1, my_homogeneity);
std::string my_unit_symbol = op.getOutput<std::string>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.custom_unit() # operator instantiation
op.inputs.unit_strings.connect(my_unit_strings)
op.inputs.homogeneity.connect(my_homogeneity)
my_unit_symbol = op.outputs.unit_symbol()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.custom_unit() # operator instantiation
op.inputs.unit_strings.Connect(my_unit_strings)
op.inputs.homogeneity.Connect(my_homogeneity)
my_unit_symbol = op.outputs.unit_symbol.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.