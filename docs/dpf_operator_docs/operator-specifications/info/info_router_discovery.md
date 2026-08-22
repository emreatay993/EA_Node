---
category: info
plugin: documentation
license: None
---

# info:router discovery

**Version: 0.0.0**

## Description

An operator providing information about operators delegating work to other operators based on namespace and filetype associations

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| info |[`data_tree`](../../core-concepts/dpf-types.md#data-tree) | Contains 3 sub DataTrees, "router_map" (operator: [filetypes]), "namespace_ext_map" (filetype: namespace) and "aliases" (operator name: alias) |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: info

 **Plugin**: documentation

 **Scripting name**: None

 **Full name**: None

 **Internal name**: info::router_discovery

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("info::router_discovery"); // operator instantiation
ansys::dpf::DataTree my_info = op.getOutput<ansys::dpf::DataTree>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.info.None() # operator instantiation
my_info = op.outputs.info()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.info.None() # operator instantiation
my_info = op.outputs.info.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.