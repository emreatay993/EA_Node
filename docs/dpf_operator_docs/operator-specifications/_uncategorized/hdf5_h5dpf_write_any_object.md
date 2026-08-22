---
category: None
plugin: N/A
license: None
---

# hdf5::h5dpf::write_any_object

**Version: 0.0.0**

## Description

Reads the number of objects of requested type.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin -7</strong>|  h5_chunk_size |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Size of each HDF5 chunk in kilobytes (KB). Default: 1 MB when compression is enabled; for uncompressed datasets, the default is the full dataset size x dimension. |
| <strong>Pin -6</strong>|  append_mode |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Experimental: Allow appending chunked data to the file. This disables fields container content deduplication. |
| <strong>Pin -5</strong>|  dataset_size_compression_threshold |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Integer value that defines the minimum dataset size (in bytes) to use h5 native compression Applicable for arrays of floats, doubles and integers. |
| <strong>Pin -2</strong>|  h5_native_compression |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`abstract_data_tree`](../../core-concepts/dpf-types.md#data-tree) | Integer value / DataTree that defines the h5 native compression used For Integer Input {0: No Compression (default); 1-9: GZIP Compression : 9 provides maximum compression but at the slowest speed.}For DataTree Input {type: None / GZIP / ZSTD; level: GZIP (1-9) / ZSTD (1-20); num_threads: ZSTD (>0)} |
| <strong>Pin -1</strong>|  export_floats |[`bool`](../../core-concepts/dpf-types.md#standard-types) | converts double to float to reduce file size (default is true) |
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  filename |[`string`](../../core-concepts/dpf-types.md#standard-types) | name of the output file that will be generated (utf8). |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  object_name |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  object |[`any`](../../core-concepts/dpf-types.md#any) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | data_sources filled with the H5 generated file path. |
|  **Pin 1**| streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | streams with the H5 file. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: hdf5::h5dpf::write_any_object

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("hdf5::h5dpf::write_any_object"); // operator instantiation
op.connect(-7, my_h5_chunk_size);
op.connect(-6, my_append_mode);
op.connect(-5, my_dataset_size_compression_threshold);
op.connect(-2, my_h5_native_compression);
op.connect(-1, my_export_floats);
op.connect(0, my_filename);
op.connect(2, my_object_name);
op.connect(4, my_object);
ansys::dpf::DataSources my_data_sources = op.getOutput<ansys::dpf::DataSources>(0);
ansys::dpf::Streams my_streams_container = op.getOutput<ansys::dpf::Streams>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.h5_chunk_size.connect(my_h5_chunk_size)
op.inputs.append_mode.connect(my_append_mode)
op.inputs.dataset_size_compression_threshold.connect(my_dataset_size_compression_threshold)
op.inputs.h5_native_compression.connect(my_h5_native_compression)
op.inputs.export_floats.connect(my_export_floats)
op.inputs.filename.connect(my_filename)
op.inputs.object_name1.connect(my_object_name1)
op.inputs.object_name2.connect(my_object_name2)
op.inputs.object1.connect(my_object1)
op.inputs.object2.connect(my_object2)
my_data_sources = op.outputs.data_sources()
my_streams_container = op.outputs.streams_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.h5_chunk_size.Connect(my_h5_chunk_size)
op.inputs.append_mode.Connect(my_append_mode)
op.inputs.dataset_size_compression_threshold.Connect(my_dataset_size_compression_threshold)
op.inputs.h5_native_compression.Connect(my_h5_native_compression)
op.inputs.export_floats.Connect(my_export_floats)
op.inputs.filename.Connect(my_filename)
op.inputs.object_name.Connect(my_object_name)
op.inputs.object.Connect(my_object)
my_data_sources = op.outputs.data_sources.GetData()
my_streams_container = op.outputs.streams_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.