---
category: None
plugin: N/A
license: None
---

# gdc provider reader

**Version: 0.0.0**

## Description

Read the data related to a gdc provider.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong>|  streams |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | Result file container allowed to be kept open to cache data. |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | Result file path container, used if no streams are set. |
| <strong>Pin 5</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  gdc_provider |[`string`](../../core-concepts/dpf-types.md#standard-types) | Name of the gdc provider requested (e.g., 'materials', 'sections'). |
| <strong>Pin 6</strong>|  properties_name |[`string`](../../core-concepts/dpf-types.md#standard-types), [`vector<string>`](../../core-concepts/dpf-types.md#standard-types) | Name of the requested properties. Can be a single string or vector of strings. If not provided, all available properties will be read. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| property_data |[`any_collection`](../../core-concepts/dpf-types.md#any-collection) | Requested data as Collection<Any> objects, one per requested property. Each Any contains the appropriate container type based on the property type (FieldsContainer, PropertyFieldsContainer, or StringFieldsContainer). |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: gdc_provider_reader

 **Full name**: None

 **Internal name**: gdc_provider_reader

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("gdc_provider_reader"); // operator instantiation
op.connect(3, my_streams);
op.connect(4, my_data_sources);
op.connect(5, my_gdc_provider);
op.connect(6, my_properties_name);
ansys::dpf::AnyCollection my_property_data = op.getOutput<ansys::dpf::AnyCollection>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.gdc_provider_reader() # operator instantiation
op.inputs.streams.connect(my_streams)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.gdc_provider.connect(my_gdc_provider)
op.inputs.properties_name.connect(my_properties_name)
my_property_data = op.outputs.property_data()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.gdc_provider_reader() # operator instantiation
op.inputs.streams.Connect(my_streams)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.gdc_provider.Connect(my_gdc_provider)
op.inputs.properties_name.Connect(my_properties_name)
my_property_data = op.outputs.property_data.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.