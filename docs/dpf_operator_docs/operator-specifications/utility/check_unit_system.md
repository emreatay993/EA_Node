---
category: utility
plugin: core
license: None
---

# utility:check unit system

**Version: 0.0.0**

## Description

Checks correctness of a new unit system defined from its base unit strings (Length, Mass, Time, Temperature, Electric Charge, and Angle).

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  unit_strings |[`string`](../../core-concepts/dpf-types.md#standard-types) | Semicolon separated list of base units |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| unit_system_isok |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Correctness of Unit System |
|  **Pin 1**| error_message |[`string`](../../core-concepts/dpf-types.md#standard-types) | If not valid, error message |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: check_unit_system

 **Full name**: utility.check_unit_system

 **Internal name**: check_unit_system

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("check_unit_system"); // operator instantiation
op.connect(0, my_unit_strings);
bool my_unit_system_isok = op.getOutput<bool>(0);
std::string my_error_message = op.getOutput<std::string>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.check_unit_system() # operator instantiation
op.inputs.unit_strings.connect(my_unit_strings)
my_unit_system_isok = op.outputs.unit_system_isok()
my_error_message = op.outputs.error_message()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.check_unit_system() # operator instantiation
op.inputs.unit_strings.Connect(my_unit_strings)
my_unit_system_isok = op.outputs.unit_system_isok.GetData()
my_error_message = op.outputs.error_message.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.