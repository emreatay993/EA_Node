---
category: metadata
plugin: cgns
license: None
---

# metadata:mesh property provider

**Version: 0.0.0**

## Description

Reads a property related to the mesh, defined by its name, by calling the readers defined by the data sources.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | result file container allowed to be kept open to cache data |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | result file path container, used if no streams are set |
| <strong>Pin 13</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  property_name |[`string`](../../core-concepts/dpf-types.md#standard-types) | Supported property names are: 'named_selection_names' and 'named_selection'. |
| <strong>Pin 17</strong>|  property_identifier |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`string`](../../core-concepts/dpf-types.md#standard-types) | Retrieves a property at a given index or by name. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| property |[`string_field`](../../core-concepts/dpf-types.md#string-field), [`scoping`](../../core-concepts/dpf-types.md#scoping) | meshed region |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: metadata

 **Plugin**: cgns

 **Scripting name**: None

 **Full name**: None

 **Internal name**: cgns::cgns::mesh_property_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("cgns::cgns::mesh_property_provider"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
op.connect(13, my_property_name);
op.connect(17, my_property_identifier);
ansys::dpf::StringField my_property = op.getOutput<ansys::dpf::StringField>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.property_name.connect(my_property_name)
op.inputs.property_identifier.connect(my_property_identifier)
my_property_as_string_field = op.outputs.property_as_string_field()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.property_name.Connect(my_property_name)
op.inputs.property_identifier.Connect(my_property_identifier)
my_property = op.outputs.property.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.