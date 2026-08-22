---
category: None
plugin: core
license: None
---

# DerivableInput

**Version: 0.0.0**

## Description

Defines a mathematical symbol usable for derivation.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  field |[`field`](../../core-concepts/dpf-types.md#field), [`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Field or fields container to associate with the mathematical symbol |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  symbol |[`string`](../../core-concepts/dpf-types.md#standard-types) | Symbol name for use in derivative operations |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  derivate_wrt |[`string`](../../core-concepts/dpf-types.md#standard-types) | Variable with respect to which derivatives are computed (internal use) |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| field |[`field`](../../core-concepts/dpf-types.md#field) | Field associated with the defined mathematical symbol |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: DerivableInput

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("DerivableInput"); // operator instantiation
op.connect(0, my_field);
op.connect(1, my_symbol);
op.connect(3, my_derivate_wrt);
ansys::dpf::Field my_field = op.getOutput<ansys::dpf::Field>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.field.connect(my_field)
op.inputs.symbol.connect(my_symbol)
op.inputs.derivate_wrt.connect(my_derivate_wrt)
my_field = op.outputs.field()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.field.Connect(my_field)
op.inputs.symbol.Connect(my_symbol)
op.inputs.derivate_wrt.Connect(my_derivate_wrt)
my_field = op.outputs.field.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.