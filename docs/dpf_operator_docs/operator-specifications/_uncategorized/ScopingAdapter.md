---
category: None
plugin: core
license: None
---

# ScopingAdapter

**Version: 0.0.0**

## Description

Converts a standard DPF scoping to a mapped scoping, adapting scoping format for internal use.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field_or_scoping |[`field`](../../core-concepts/dpf-types.md#field), [`scoping`](../../core-concepts/dpf-types.md#scoping) | Field (to extract scoping from) or direct scoping to be adapted |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) | Mapped scoping adapted for internal operations |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: ScopingAdapter

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("ScopingAdapter"); // operator instantiation
op.connect(0, my_field_or_scoping);
ansys::dpf::Scoping my_scoping = op.getOutput<ansys::dpf::Scoping>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.field_or_scoping.connect(my_field_or_scoping)
my_scoping = op.outputs.scoping()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.field_or_scoping.Connect(my_field_or_scoping)
my_scoping = op.outputs.scoping.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.