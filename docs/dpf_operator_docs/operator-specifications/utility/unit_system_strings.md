---
category: utility
plugin: core
license: None
---

# utility:unit system strings

**Version: 0.0.0**

## Description

Gets the unit strings from an Ansys unit system defined from its ID.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  unit_system_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Ansys Unit System ID |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| unit_strings |[`string`](../../core-concepts/dpf-types.md#standard-types) | Unit strings for the Unit System |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: unit_system_strings

 **Full name**: utility.unit_system_strings

 **Internal name**: unit_system_strings

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("unit_system_strings"); // operator instantiation
op.connect(0, my_unit_system_id);
std::string my_unit_strings = op.getOutput<std::string>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.unit_system_strings() # operator instantiation
op.inputs.unit_system_id.connect(my_unit_system_id)
my_unit_strings = op.outputs.unit_strings()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.unit_system_strings() # operator instantiation
op.inputs.unit_system_id.Connect(my_unit_system_id)
my_unit_strings = op.outputs.unit_strings.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.