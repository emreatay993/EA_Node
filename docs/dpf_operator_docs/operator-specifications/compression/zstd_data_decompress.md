---
category: compression
plugin: core
license: None
---

# compression:zstd_data_decompress

**Version: 0.0.0**

## Description

Deompressing data using zstd compression algorithm.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin -1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  ptr_mallocfree |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Activate option for handling pointers instead of vectors.Users are resposible to free the output pointer memory to avoid memory leaks.Default = False. |
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data |[`ptr(char)`](../../core-concepts/dpf-types.md#ptr(char)), [`vector<char>`](../../core-concepts/dpf-types.md#standard-types) | Data to be decompressed: If vector is input, no need of bit size. To use pointer, user needs to activate pin ptr_mallocfree |
| <strong>Pin 1</strong>|  input_bytes_size |[`uint64`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_type |[`uint32`](../../core-concepts/dpf-types.md#standard-types) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| output_data |[`ptr(char)`](../../core-concepts/dpf-types.md#ptr(char)), [`vector<double>`](../../core-concepts/dpf-types.md#standard-types), [`vector<int32>`](../../core-concepts/dpf-types.md#standard-types), [`vector<float>`](../../core-concepts/dpf-types.md#standard-types), [`vector<char>`](../../core-concepts/dpf-types.md#standard-types) |  |
|  **Pin 1**| output_bytes_size |[`uint64`](../../core-concepts/dpf-types.md#standard-types) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: compression

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: zstd_data_decompress

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("zstd_data_decompress"); // operator instantiation
op.connect(-1, my_ptr_mallocfree);
op.connect(0, my_data);
op.connect(1, my_input_bytes_size);
op.connect(2, my_data_type);
ansys::dpf::Ptr(Char) my_output_data = op.getOutput<ansys::dpf::Ptr(Char)>(0);
ansys::dpf::Uint64 my_output_bytes_size = op.getOutput<ansys::dpf::Uint64>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.compression.None() # operator instantiation
op.inputs.ptr_mallocfree.connect(my_ptr_mallocfree)
op.inputs.data.connect(my_data)
op.inputs.input_bytes_size.connect(my_input_bytes_size)
op.inputs.data_type.connect(my_data_type)
my_output_data_as_ptr(char) = op.outputs.output_data_as_ptr(char)()
my_output_bytes_size = op.outputs.output_bytes_size()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.compression.None() # operator instantiation
op.inputs.ptr_mallocfree.Connect(my_ptr_mallocfree)
op.inputs.data.Connect(my_data)
op.inputs.input_bytes_size.Connect(my_input_bytes_size)
op.inputs.data_type.Connect(my_data_type)
my_output_data = op.outputs.output_data.GetData()
my_output_bytes_size = op.outputs.output_bytes_size.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.