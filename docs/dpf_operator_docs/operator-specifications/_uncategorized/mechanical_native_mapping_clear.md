---
category: None
plugin: N/A
license: any_dpf_supported_increments
---

# clear mechanical native mapping cache

**Version: 0.0.0**

## Description

Clears the mappingManager source and target data for given src and trg mesh ids.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  source_mesh_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Source mesh id |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  target_mesh_id |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Target mesh id |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| is_clear_successful |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Returns true if the cache clear is successful. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: mechanical_native_mapping_clear

 **Full name**: None

 **Internal name**: mechanical_native_mapping::clear

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical_native_mapping::clear"); // operator instantiation
op.connect(1, my_source_mesh_id);
op.connect(3, my_target_mesh_id);
bool my_is_clear_successful = op.getOutput<bool>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.mechanical_native_mapping_clear() # operator instantiation
op.inputs.source_mesh_id.connect(my_source_mesh_id)
op.inputs.target_mesh_id.connect(my_target_mesh_id)
my_is_clear_successful = op.outputs.is_clear_successful()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.mechanical_native_mapping_clear() # operator instantiation
op.inputs.source_mesh_id.Connect(my_source_mesh_id)
op.inputs.target_mesh_id.Connect(my_target_mesh_id)
my_is_clear_successful = op.outputs.is_clear_successful.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.