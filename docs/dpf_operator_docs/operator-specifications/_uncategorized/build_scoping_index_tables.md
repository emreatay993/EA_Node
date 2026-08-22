---
category: None
plugin: core
license: None
---

# build scoping index tables

**Version: 0.0.0**

## Description

This operator allows to build scoping index tables that relate the ids from the source collection to the ids of each destination collection.This operator can be used to precompute the indices of each item of the destination collection that correspond to the indices of each source collection field ids.The property field outputs contain for each source index the corresponding index of the destination collection scoping and the index of the unique indices scopings container.
 The computation is done in a 2 step process:
 - For each entry in the destination collections in input pins 1, 2, 3..., an entry in the source collection in pin 0 is identified.These indices are stored for fast access in the outputs 1, 2, 3....
 - Then, for each scoping id in the source collection we identify the correspondind index in the destination collection.If not found, we store a - 1. The corresponding scoping built of indices is stored in pin 0.

Example : 

| Source collection                               | Destination collection 1                        | Destination collection 2                        |
| Index | label space        | Scoping Ids        | Index | label space        | Scoping Ids        | Index | label space        | Scoping Ids        |
|-------|--------------------|--------------------|-------|--------------------|--------------------|-------|--------------------|--------------------|
| 0     | {time: 1, body: 1} | {1,2,3,4,5,6,7}    | 0     | {body: 1}          | {3,5,8}            | none  |  single field      | {5,8,15,13}        |
| 1     | {time: 1, body: 2} | {11,12,13,15}      | 1     | {body: 2}          | {13,15,11}         |                                                 |
| 2     | {time: 2, body: 1} | {1,2,3,4,5,6,7}    |                                                 |                                                 |
| 3     | {time: 2, body: 2} | {11,12,13,15}      |                                                 |                                                 |

| Unique indices                | Unique indices Id PropertyField 1 | Unique indices Id PropertyField 2 |
| Index | Scoping Ids           | Index                             | Index                             |
|-------------------------------|-----------------------------------|-----------------------------------|
| 0     | {-1,-1,0,-1,1,-1,-1}  | {{0,0}, {1,1}, {0,0}, {1,1}}      | {{0,2}, {0,3}, {0,2}, {0,3}}      |
| 1     | {2,-1,0,1}            |                                   |                                   |
| 2     | {-1,-1,-1,-1,0,-1,-1} |                                   |                                   |
| 3     | {-1,-1,3,2}           |                                   |                                   |

A loop would go from : 

for (ansys::dpf::dp_index index_source = 0; index_source < source_collection.size(); index_source++)	 
{																										 
	auto item_source = source_collection.at(index_source);												 
	auto ids = item_source.scoping().ids();																 
	auto label_space = source_collection.getLabelSpace(index_source);									 
																										 
	auto destination_item_1 = destination_collection_1.getMatchingField(label_space);					 
	auto scoping_item_1 = destination_item_1.scoping();													 
	...																									 
	for (ansys::dpf::dp_index entity_index = 0; entity_index < ids.size(); entity_index++)				 
	{																									 
		auto id = ids[entity_index];																	 
		auto index_destination_item_1 = scoping_item_1.indexById(id); // time consuming map lookup		 
		if (index_destination_item_1 != -1)																 
			Operation_based_on_Destigation_item_1(index_destination_item_1);                 			 
			...																							 
	}																									 
}																										 

After modifications : 

 int size_data = 2;																										 
for (ansys::dpf::dp_index index_source = 0; index_source < source_collection.size(); index_source++)	 
{																										 
	auto item_source = source_collection.at(index_source);												 
	auto ids = item_source.scoping().ids();																 
																										 
	auto unique_indeces_1_data = unique_indeces_id_pf1.dataByIndex(index_source, size_data);			 
	auto destination_item_1 = destination_collection_1.at(unique_indeces_1_data[0]);					 
	auto data_destination_item_1 = destination_item_1.data();											 
	auto indices_item_1 = unique_indices.at(unique_indeces_1_data[1]).ids();				 
	...																									 
	for (ansys::dpf::dp_index entity_index = 0; entity_index < ids.size(); entity_index++)				 
	{																									 
		auto index_destination_item_1 = indices_item_1[entity_index]; // fast vector item recover		 
		if (index_destination_item_1 != -1)																 
			Operation_based_on_Destigation_item_1(index_destination_item_1);                 			 
			...																							 
	}																									 
}																										 



## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin -2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  unique_indices |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |
| <strong>Pin -1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  cache |[`any`](../../core-concepts/dpf-types.md#any) |  |
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  source_collection |[`any_collection`](../../core-concepts/dpf-types.md#any-collection) |  |
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  destination_collection |[`any_collection`](../../core-concepts/dpf-types.md#any-collection), [`scoping`](../../core-concepts/dpf-types.md#scoping), [`field`](../../core-concepts/dpf-types.md#field), [`property_field`](../../core-concepts/dpf-types.md#property-field), [`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field), [`string_field`](../../core-concepts/dpf-types.md#string-field), [`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin -1**| cache |[`any`](../../core-concepts/dpf-types.md#any) |  |
|  **Pin 0**| unique_indices |[`scopings_container`](../../core-concepts/dpf-types.md#scopings-container) |  |
|  **Pin 1**| unique_indices_id |[`property_field`](../../core-concepts/dpf-types.md#property-field) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: build_scoping_index_tables

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("build_scoping_index_tables"); // operator instantiation
op.connect(-2, my_unique_indices);
op.connect(-1, my_cache);
op.connect(0, my_source_collection);
op.connect(1, my_destination_collection);
ansys::dpf::Any my_cache = op.getOutput<ansys::dpf::Any>(-1);
ansys::dpf::ScopingsContainer my_unique_indices = op.getOutput<ansys::dpf::ScopingsContainer>(0);
ansys::dpf::PropertyField my_unique_indices_id = op.getOutput<ansys::dpf::PropertyField>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.unique_indices.connect(my_unique_indices)
op.inputs.cache.connect(my_cache)
op.inputs.source_collection.connect(my_source_collection)
op.inputs.destination_collection1.connect(my_destination_collection1)
op.inputs.destination_collection2.connect(my_destination_collection2)
my_cache = op.outputs.cache()
my_unique_indices = op.outputs.unique_indices()
my_unique_indices_id = op.outputs.unique_indices_id()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.unique_indices.Connect(my_unique_indices)
op.inputs.cache.Connect(my_cache)
op.inputs.source_collection.Connect(my_source_collection)
op.inputs.destination_collection.Connect(my_destination_collection)
my_cache = op.outputs.cache.GetData()
my_unique_indices = op.outputs.unique_indices.GetData()
my_unique_indices_id = op.outputs.unique_indices_id.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.