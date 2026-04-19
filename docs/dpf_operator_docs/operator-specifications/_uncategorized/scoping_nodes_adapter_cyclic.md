---
category: None
plugin: core
license: None
---

# scoping::nodes_adapter_cyclic

**Version: 0.0.0**

## Description

Adapt a mesh scoping with the correspondind high/low ids.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  meshScoping |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container), [`scoping`](../../core-concepts/dpf-types.md#scoping) | meshScoping. |
| <strong>Pin 16</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  CyclicSupport |[`cyclic_support`](../../core-concepts/dpf-types.md#cyclic-support) | CyclicSupport |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 1**| scopings_container |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) | scopings_container. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: scoping::nodes_adapter_cyclic

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("scoping::nodes_adapter_cyclic"); // operator instantiation
op.connect(1, my_meshScoping);
op.connect(16, my_CyclicSupport);
ansys::dpf::ScopingsContainer my_scopings_container = op.getOutput<ansys::dpf::ScopingsContainer>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.meshScoping.connect(my_meshScoping)
op.inputs.CyclicSupport.connect(my_CyclicSupport)
my_scopings_container = op.outputs.scopings_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.meshScoping.Connect(my_meshScoping)
op.inputs.CyclicSupport.Connect(my_CyclicSupport)
my_scopings_container = op.outputs.scopings_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.