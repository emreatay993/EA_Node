---
category: None
plugin: core
license: None
---

# migrate to dpf result file

**Version: 0.0.0**

## Description

Read mesh properties from the results files contained in the streams or data sources and make those properties available through a mesh selection manager in output.User can input a GenericDataContainer that will map an item to a result name. Example of Map: {{ default: wf1}, {EUL: wf2}, {ENG_SE: wf3}}.

## Supported file types

This operator supports the following keys ([file formats](../../index.md#overview-of-dpf)) for each listed namespace (plugin/solver):

- hdf5: h5dpf 

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin -6</strong>|  append_mode |[`bool`](../../core-concepts/dpf-types.md#standard-types) | BETA Option: Allow appending chunked data to the file. This disables fields container content deduplication. |
| <strong>Pin -5</strong>|  dataset_size_compression_threshold |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) | Integer value that defines the minimum dataset size (in bytes) to use h5 native compression Applicable for arrays of floats, doubles and integers. |
| <strong>Pin -4</strong>|  file_namespace |[`string`](../../core-concepts/dpf-types.md#standard-types) | String defining the namespace of the result file |
| <strong>Pin -3</strong>|  file_format |[`string`](../../core-concepts/dpf-types.md#standard-types) | String defining the format of the result file |
| <strong>Pin -2</strong>|  native_compression |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) | Integer value that defines the native compression used  |
| <strong>Pin -1</strong>|  export_floats |[`bool`](../../core-concepts/dpf-types.md#standard-types), [`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) | Converts double to float to reduce file size (default is true).If False, nodal results are exported as double precision and elemental results as single precision. |
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  filename |[`string`](../../core-concepts/dpf-types.md#standard-types) | filename of the migrated file |
| <strong>Pin 1</strong>|  comma_separated_list_of_results |[`string`](../../core-concepts/dpf-types.md#standard-types) | list of results (source operator names) separated by semicolons that will be stored. (Example: U;S;EPEL). If empty, all available results will be converted.   |
| <strong>Pin 2</strong>|  all_time_sets |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Deprecated. Please use filtering workflows instead to select time scoping. Default is false. |
| <strong>Pin 3</strong>|  streams |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | streams (result file container) (optional) |
| <strong>Pin 4</strong>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | if the stream is null then we need to get the file path from the data sources |
| <strong>Pin 6</strong>|  compression_workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow), [`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) | BETA Option: Applies input compression workflow. |
| <strong>Pin 7</strong>|  filtering_workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow), [`generic_data_container`](../../core-concepts/dpf-types.md#generic-data-container) | Applies input filtering workflow. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| migrated_file |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: migrate_to_dpf_file

 **Full name**: None

 **Internal name**: migrate_file

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("migrate_file"); // operator instantiation
op.connect(-6, my_append_mode);
op.connect(-5, my_dataset_size_compression_threshold);
op.connect(-4, my_file_namespace);
op.connect(-3, my_file_format);
op.connect(-2, my_native_compression);
op.connect(-1, my_export_floats);
op.connect(0, my_filename);
op.connect(1, my_comma_separated_list_of_results);
op.connect(2, my_all_time_sets);
op.connect(3, my_streams);
op.connect(4, my_data_sources);
op.connect(6, my_compression_workflow);
op.connect(7, my_filtering_workflow);
ansys::dpf::DataSources my_migrated_file = op.getOutput<ansys::dpf::DataSources>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.migrate_to_dpf_file() # operator instantiation
op.inputs.append_mode.connect(my_append_mode)
op.inputs.dataset_size_compression_threshold.connect(my_dataset_size_compression_threshold)
op.inputs.file_namespace.connect(my_file_namespace)
op.inputs.file_format.connect(my_file_format)
op.inputs.native_compression.connect(my_native_compression)
op.inputs.export_floats.connect(my_export_floats)
op.inputs.filename.connect(my_filename)
op.inputs.comma_separated_list_of_results.connect(my_comma_separated_list_of_results)
op.inputs.all_time_sets.connect(my_all_time_sets)
op.inputs.streams.connect(my_streams)
op.inputs.data_sources.connect(my_data_sources)
op.inputs.compression_workflow.connect(my_compression_workflow)
op.inputs.filtering_workflow.connect(my_filtering_workflow)
my_migrated_file = op.outputs.migrated_file()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.migrate_to_dpf_file() # operator instantiation
op.inputs.append_mode.Connect(my_append_mode)
op.inputs.dataset_size_compression_threshold.Connect(my_dataset_size_compression_threshold)
op.inputs.file_namespace.Connect(my_file_namespace)
op.inputs.file_format.Connect(my_file_format)
op.inputs.native_compression.Connect(my_native_compression)
op.inputs.export_floats.Connect(my_export_floats)
op.inputs.filename.Connect(my_filename)
op.inputs.comma_separated_list_of_results.Connect(my_comma_separated_list_of_results)
op.inputs.all_time_sets.Connect(my_all_time_sets)
op.inputs.streams.Connect(my_streams)
op.inputs.data_sources.Connect(my_data_sources)
op.inputs.compression_workflow.Connect(my_compression_workflow)
op.inputs.filtering_workflow.Connect(my_filtering_workflow)
my_migrated_file = op.outputs.migrated_file.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.