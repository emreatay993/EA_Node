---
category: result
plugin: mapdl
license: None
---

# result:cms node position provider

**Version: 0.0.0**

## Description

Read nodes of the cms elements. Extract node ids, node locations from a subfile.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | Data_sources (must contain at least one subfile). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| fields_container |[`field`](../../core-concepts/dpf-types.md#field) | Fields container containing in this order : node ids, node locations. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: cms_node_position_provider

 **Full name**: result.cms_node_position_provider

 **Internal name**: cms_node_position_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cms_node_position_provider"); // operator instantiation
op.connect(4, my_data_sources);
ansys::dpf::Field my_fields_container = op.getOutput<ansys::dpf::Field>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.cms_node_position_provider() # operator instantiation
op.inputs.data_sources.connect(my_data_sources)
my_fields_container = op.outputs.fields_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.cms_node_position_provider() # operator instantiation
op.inputs.data_sources.Connect(my_data_sources)
my_fields_container = op.outputs.fields_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.